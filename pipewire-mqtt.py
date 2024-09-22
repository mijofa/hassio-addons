#!/usr/bin/python3
"""Monitor pipewire state."""
import json
import socket
import subprocess
import typing
import uuid

import dns.resolver
import paho.mqtt.client

# FIXME: Make async I/O work

# In my experience, the role can be whatever string I want it to be.
# But in practice, it's barely actually used.
# And in the documentation there's a limited number of options for it.
# https://www.freedesktop.org/wiki/Software/PulseAudio/Documentation/Developer/Clients/ApplicationProperties/#pa_prop_media_role
PW_ROLE_NUM_STREAMS: dict[str, set] = {
    # Should be ignored as this is what we're controling anyway.
    "music": set(),
    # Must mute the music and steal all attention
    "phone": set(),
    # Should probably dim the lights the same as TV inhibitor
    "game": set(),
    # Should this dim the lights? Probably not, this'll be YouTube videos and such
    "video": set(),
    # Chat notification blips, should this mute the music?
    # Ideally, probably not.
    # Realistically I probably can't differentiate it from 'phone' because I'm setting role at the application level.
    "event": set(),
    # I personally don't expect to use this one currently.
    # It maybe shouldn't mute the music, but maybe lower the music volume.
    "a11y": set(),
    # Wtf, are these ever even gonna be used?
    "animation": set(),
    "production": set(),
    # FIXME: Should this be phone?
    #        This is what I'm seeing with Discord, even though I've set `Environment=PULSE_PROP="media.role=phone"`
    "communication": set(),
    # Not a real option, I'm just using this for anything that doesn't have a defined role
    # FIXME: Should probably use this for any roles that are not in this list either
    'other': set(),
}

MQTT_TOPIC_BASE: str = f"homeassistant/binary_sensor/{socket.gethostname()}"
AVAILABILITY_TOPIC: str = '/'.join((MQTT_TOPIC_BASE, "availability"))


def mqtt_discovery(client: paho.mqtt.client.Client):
    """Send MQTT discovery info for Home Assistant."""
    # FIXME: Why do the DLNA & Nmap devices combine into one, but I can't make this combine with them?
    mac_address: str = f'{uuid.getnode():02x}'
    hex_mac: str = ':'.join(mac_address[i:i + 2] for i in range(0, len(mac_address), 2))

    for role in PW_ROLE_NUM_STREAMS:
        client.publish(topic='/'.join((MQTT_TOPIC_BASE, f"pipewire_{role}", "config")),
                       payload=json.dumps({
                           "availability_topic": AVAILABILITY_TOPIC,
                           "device": {
                               "connections": [("mac", hex_mac)],
                               "name": socket.gethostname()},
                           "device_class": "sound",
                           # "category": "config/diagnostic",  # FIXME: wtf is this?
                           # "icon": "mdi:monitor-speaker",
                           # # FIXME: Not currently sending attributes anywhere
                           # "json_attributes_topic": '/'.join((MQTT_TOPIC_BASE, "music_inhibitor", "attributes")),
                           "name": f"Audio playback - {role}",
                           "state_topic": '/'.join((MQTT_TOPIC_BASE, f"pipewire_{role}", "state")),
                           "unique_id": 'pipewire'+hex_mac+role,
                       }),
                       retain=True)


def read_pretty_json_list(fp: typing.TextIO):
    """Read & decode the next pretty-printed JSON list from file object."""
    line: str = fp.readline()
    if line != "[\n":
        raise NotImplementedError("Must start with a '['")

    json_string = line
    while line != "]\n":
        line: str = fp.readline()
        json_string += line

    return json.loads(json_string)


def pipewire_events():
    """."""
    pw_dump = subprocess.Popen(['pw-dump', '--monitor', '--no-colors'],
                               text=True, stdout=subprocess.PIPE)
    while pw_dump.poll() is None:
        for event in read_pretty_json_list(pw_dump.stdout):
            yield event


# Since upstream **still** hasn't fixed this 3yr old bug
# https://github.com/eclipse/paho.mqtt.python/issues/493
# I've copy/pasted upstream's connect_srv function to fix it internally.
# I've also pushed my own pull request for them
# https://github.com/eclipse/paho.mqtt.python/pull/759
# but I get the feeling it's going to be ignored
# -- mijofa, 2023-10-23
def connect_srv(mqtt_client, domain=None, *args, **kwargs):
    """Connect to a remote broker.

    domain is the DNS domain to search for SRV records; if None,
    try to determine local domain name.
    All other args are used as is for connect()
    """
    if domain is None:
        domain = socket.getfqdn()
        domain = domain[domain.find('.') + 1:]

    try:
        rr = '_mqtt._tcp.%s' % domain
        if mqtt_client._ssl:
            # IANA specifies secure-mqtt (not mqtts) for port 8883
            rr = '_secure-mqtt._tcp.%s' % domain
        answers = []
        for answer in dns.resolver.resolve(rr, dns.rdatatype.SRV):
            addr = answer.target.to_text()[:-1]
            answers.append(
                (addr, answer.port, answer.priority, answer.weight))
    except (dns.resolver.NXDOMAIN,
            dns.resolver.NoAnswer,
            dns.resolver.NoNameservers):
        raise ValueError("No answer/NXDOMAIN for SRV in %s" % (domain))

    # FIXME: doesn't account for weight
    for answer in answers:
        host, port, prio, weight = answer

        try:
            return mqtt_client.connect(host, port, *args, **kwargs)
        except Exception:
            raise

    raise ValueError("No SRV hosts responded")


mqtt_client = paho.mqtt.client.Client()
# NOTE: The will must be set before connecting.
mqtt_client.will_set(topic=AVAILABILITY_TOPIC, payload='offline')

# FIXME: Try anonymous, and fallback on guest:guest when that fails
mqtt_client.username_pw_set(username='guest', password='guest')
connect_srv(mqtt_client)
mqtt_client.loop_start()

# FIXME: Can I make this wait until after the first load of events is handled before first updating the payload?
#        Because that first set of dumped events tends to bounce the inhibitor on/off annoyingly.
# FIXME: Notify Systemd that we're ready, perhaps at the same time as ^ FIXME?
mqtt_discovery(mqtt_client)
mqtt_client.publish(topic=AVAILABILITY_TOPIC, payload='online', retain=False)

# Set everything to off before we get started
for mqtt_topic in ('/'.join((MQTT_TOPIC_BASE, f"pipewire_{role}", "state")) for role in PW_ROLE_NUM_STREAMS):
    mqtt_client.publish(topic=mqtt_topic,
                        payload='OFF',
                        retain=True)

def add_stream(stream_id: int, stream_role: typing.Literal[*PW_ROLE_NUM_STREAMS.keys()], app_id: str = ''):
    # Don't bother logging & publishing an update if we've already handled this one
    # Just reduces log spam
    if stream_id in PW_ROLE_NUM_STREAMS[stream_role]:
        return

    PW_ROLE_NUM_STREAMS[stream_role].add(stream_id)
    print(f"{stream_id} - new {stream_role} stream",
            app_id,
            f"total = {len(PW_ROLE_NUM_STREAMS[stream_role])}",
            sep=', ')
    mqtt_client.publish(topic='/'.join((MQTT_TOPIC_BASE,
                                        f"pipewire_{stream_role}",
                                        "state")),
                        payload='ON',
                        retain=True)

    # Keep record of what role this was so that we can track it on deletion
    playback_streams[stream_id] = stream_role


def subtract_stream(stream_id: int):
    if stream_id not in playback_streams:
        return
    if (stream_role := playback_streams.pop(stream_id)) in PW_ROLE_NUM_STREAMS:
        PW_ROLE_NUM_STREAMS[stream_role].remove(stream_id)
        print(f"{stream_id} - del {stream_role} stream,",
            f"total = {len(PW_ROLE_NUM_STREAMS[stream_role])}",
            PW_ROLE_NUM_STREAMS[stream_role])
        if len(PW_ROLE_NUM_STREAMS[stream_role]) == 0:
            mqtt_client.publish(topic='/'.join((MQTT_TOPIC_BASE, f"pipewire_{stream_role}", "state")),
                                payload='OFF',
                                retain=True)


# This is a mapping of {stream_id: stream_role} so that we don't have to iterate all of 'PW_ROLE_NUM_STREAMS' to find a stream.
playback_streams: dict[int, str] = {}
for ev in pipewire_events():
    if 'type' not in ev and ev.get('info') is None:
        # This is a node being removed, but we don't know what type of node
        subtract_stream(ev['id'])

    elif ev.get('type') == 'PipeWire:Interface:Node':
        match ev['info']['props'].get('media.class'):
            case 'Stream/Output/Audio':
                # Pretty sure this is a playback stream.
                if ev['info']['props'].get('node.passive', False) is True:
                    # I've seen this with internal loopback & echo canceling modules.
                    continue
                elif 'state' not in ev['info']['change-mask'] and 'params' not in ev['info']['change-mask']:
                    # Don't care about anything other than state changes
                    continue
                if ev['info']['state'] == 'idle':
                    # Media paused? Firefox sets this when a video is paused
                    subtract_stream(ev['id'])
                    continue

                # FIXME: WTF is this titlecased?
                stream_role: str = ev['info']['props'].get('media.role', 'other').lower()
                if stream_role not in PW_ROLE_NUM_STREAMS:
                    stream_role = 'other'

                add_stream(stream_id=ev['id'],
                           stream_role=stream_role,
                           app_id=f"""{ev['info']['props'].get('node.name',
                                        ev['info']['props'].get('application.name',
                                            ev['info']['props'].get('application.process.binary', '')))}[{ev['info']['props'].get('application.process.id')}]""")
            case 'Audio/Sink':
                # Pretty sure this is output sinks
                if 'params' not in ev['info']['change-mask']:
                    # Don't care about changes outside of 'params'
                    continue

    # Ping the availability topic in case HA has restarted and forgotten latest state
    mqtt_client.publish(topic=AVAILABILITY_TOPIC, payload='online', retain=False)
