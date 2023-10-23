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


# Since upstream **still** hasn't fixed this 3yr old bug
# https://github.com/eclipse/paho.mqtt.python/issues/493
# I've copy/pasted upstream's connect_srv function myself.
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
# FIXME: Try anonymous, and fallback on guest:guest when that fails
mqtt_client.username_pw_set(username='guest', password='guest')
connect_srv(mqtt_client)
mqtt_client.loop_start()
# FIXME: This doesn't seem to be working
mqtt_client.will_set(topic=MQTT_TOPIC, payload='unavailable', retain=True)

previous_payload = None
playback_streams = {}
output_sinks = {}
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
                if 'state' not in ev['info']['change-mask']:
                    # Don't care about anything other than state changes
                    continue

                playback_streams[ev['id']] = (ev['info']['state'],
                                              ev['info']['props'])
                print(ev['info']['state'],
                      ev['info']['props']['application.name'],
                      ev['info']['props'].get('media.role'))
            case 'Audio/Sink':
                # Pretty sure this is output sinks
                if 'params' not in ev['info']['change-mask']:
                    # Don't care about changes outside of 'params'
                    continue

                print(ev['info']['props']['node.name'],
                      ev['info']['props']['node.description'])
                print(ev['info']['params']['Props'][0]['mute'],
                      # FIXME: What math do I need for a single volume number?
                      ev['info']['params']['Props'][0]['volume'],
                      ev['info']['params']['Props'][0]['channelVolumes'])

    if any((state == 'running' for state, props in playback_streams.values())):
        payload = 'on'
    else:
        payload = 'off'
    if payload != previous_payload:
        print('MQTT>', MQTT_TOPIC, payload)
        mqtt_client.publish(topic=MQTT_TOPIC,
                            payload=payload,
                            retain=True)
        previous_payload = payload
