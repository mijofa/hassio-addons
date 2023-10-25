#!/usr/bin/python3
"""Monitor pipewire state."""
import json
import subprocess
import socket
import dns.resolver

import paho.mqtt.client

# FIXME: Make async I/O work

# FIXME: Set up Home Assistant's MQTT discovery per:
#        https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery
#        Instead of relying on a single static topic.
MQTT_TOPIC = 'update/input_boolean/music_inhibitor_mqtt'
# FIXME: Handle this in Home Assistant
PASSIVE_ROLES = ['Music']


def read_pretty_json_list(fp):
    """Read & decode the next pretty-printed JSON list from file object."""
    line = fp.readline()
    if line != "[\n":
        raise NotImplementedError("Must start with a '['")

    json_string = line
    while line != "]\n":
        line = fp.readline()
        json_string += line

    return json.loads(json_string)


def pipewire_events():
    """."""
    pw_dump = subprocess.Popen(['pw-dump', '--monitor', '--no-colors'],
                               text=True, stdout=subprocess.PIPE)
    while pw_dump.poll() is None:
        for ev in read_pretty_json_list(pw_dump.stdout):
            yield ev


def _vol_to_percentage(vol):
    """Return the given volume as a percentage."""
    # I don't understand what the input number actually is,
    # or the math behind fixing this.
    # But I found someone else doing this with awk:
    # https://gist.github.com/venam/bd453b4fd673ff8abb9323e69f182045
    # and doing the same in Python has worked with everything I've thrown at it
    # I added 'round' because It keeps giving me things like '0.5499878785207348',
    # when pavucontrol says '55%'
    return round(vol**(1 / 3), 2)


def get_sink_state(sink_info):
    """
    Get the current volume (as a percentage) from the given sink info.

    Returns:
    * True if muted, False if note
    * The average volume across all channels
    * The name & volume of each channel
    """
    channels = {}
    for num, name in enumerate(sink_info['params']['Props'][0]['channelMap']):
        if sink_info['params']['Props'][0]['softVolumes'][num] != 1 and \
           sink_info['params']['Props'][0]['softVolumes'][num] != sink_info['params']['Props'][0]['channelVolumes'][num]:
            raise NotImplementedError("Not seen in testing")
        else:
            channels[name] = _vol_to_percentage(sink_info['params']['Props'][0]['channelVolumes'][num])

    # In testing I never saw 'softMute' be True,
    # so I'm just kind of assuming how this works.
    muted = sink_info['params']['Props'][0]['mute'] or sink_info['params']['Props'][0]['softMute']

    return (muted, sum(channels.values()) / len(channels), channels)


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
mqtt_client.will_set(topic=MQTT_TOPIC, payload='unavailable', retain=True)

# FIXME: Try anonymous, and fallback on guest:guest when that fails
mqtt_client.username_pw_set(username='guest', password='guest')
connect_srv(mqtt_client)
mqtt_client.loop_start()

previous_payload = None
playback_streams = {}
output_sinks = {}
# FIXME: Can I make this wait until after the first load of events is handled before first updating the payload?
#        Because that first set of dumped events tends to bounce the inhibitor on/off annoyingly.
# FIXME: Notify Systemd that we're ready, perhaps at the same time as ^ FIXME?
for ev in pipewire_events():
    if 'type' not in ev and ev.get('info') is None:
        # This is a node being removed, but we don't know what type of node
        if ev['id'] in playback_streams:
            del playback_streams[ev['id']]
        if ev['id'] in output_sinks:
            del output_sinks[ev['id']]
        # FIXME: Trigger an update of some sort.
    elif ev.get('type') == 'PipeWire:Interface:Node':
        match ev['info']['props'].get('media.class'):
            case 'Stream/Output/Audio':
                # Pretty sure this is a playback stream.
                if ev['info']['props'].get('node.passive', False) is True:
                    # I've seen this with internal loopback & echo canceling modules.
                    continue
                elif 'state' not in ev['info']['change-mask']:
                    # Don't care about anything other than state changes
                    continue

                playback_streams[ev['id']] = (ev['info']['state'],
                                              ev['info']['props'])
                print(ev['info']['state'], 'playback stream',
                      ev['info']['props']['application.name'],
                      ev['info']['props'].get('media.role'))
            case 'Audio/Sink':
                # Pretty sure this is output sinks
                if 'params' not in ev['info']['change-mask']:
                    # Don't care about changes outside of 'params'
                    continue

                output_sinks[ev['id']] = (ev['info']['state'], get_sink_state(ev['info']))
                print(ev['info']['state'], 'output sink',
                      ev['info']['props']['node.description'],
                      ev['info']['props']['node.name'],
                      get_sink_state(ev['info']))

    if any((props.get('media.role') not in PASSIVE_ROLES for state, props in playback_streams.values()
            if state == 'running' for state, props in playback_streams.values())):
        payload = 'on'
    else:
        payload = 'off'
    if payload != previous_payload:
        print('MQTT>', MQTT_TOPIC, payload)
        mqtt_client.publish(topic=MQTT_TOPIC,
                            payload=payload,
                            retain=True)
        previous_payload = payload
