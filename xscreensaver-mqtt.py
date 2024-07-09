#!/usr/bin/python3
"""Monitor pipewire state."""
import dns.resolver
import json
import socket
import subprocess
import uuid

import paho.mqtt.client

# FIXME: Make async I/O work

# FIXME: Set up Home Assistant's MQTT discovery per:
#        https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery
#        Instead of relying on a single static topic.
# MQTT_TOPIC = 'update/input_boolean/music_inhibitor_mqtt'
EVENT_TO_MQTT = {
    'UNBLANK': 'UNLOCKED',
    'BLANK': 'LOCKING',
    'LOCK': 'LOCKED',
}

MQTT_TOPIC_BASE = f"homeassistant/lock/{socket.gethostname()}/xscrensaver"
AVAILABILITY_TOPIC = '/'.join((MQTT_TOPIC_BASE, "availability"))



def mqtt_discovery(mqtt_client):
    """Send MQTT discovery info for Home Assistant."""
    # FIXME: Why do the DLNA & Nmap devices combine into one, but I can't make this combine with them?
    mac_address = f'{uuid.getnode():02x}'
    unique_id = ':'.join(mac_address[i:i + 2] for i in range(0, len(mac_address), 2))

    mqtt_client.publish(topic='/'.join((MQTT_TOPIC_BASE, "config")),
                        payload=json.dumps({
                            "availability_topic": AVAILABILITY_TOPIC,
                            "device": {
                                "connections": [("mac", unique_id)],
                                "name": socket.gethostname()},
                            "unique_id": f'xscreensaver_mqtt:{uuid.getnode():02x}',
                            # "category": "config/diagnostic",  # FIXME: wtf is this?
                            # "icon": "mdi:monitor-speaker",
                            # FIXME: Not currently sending attributes anywhere
                            "json_attributes_topic": '/'.join((MQTT_TOPIC_BASE, "attributes")),
                            "name": "xscreensaver",
                            "state_topic": '/'.join((MQTT_TOPIC_BASE, "state")),
                            "command_topic": '/'.join((MQTT_TOPIC_BASE, "command")),
                        }),
                        retain=True)

    return '/'.join((MQTT_TOPIC_BASE, "state")), '/'.join((MQTT_TOPIC_BASE, "command"))


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


def command_callback(client, unknown, message):
    if message.topic != command_topic:
        raise Excaption("Callback called from the wrong topic")
    command = message.payload.decode()
    if command == 'LOCK':
        return subprocess.check_call(['xscreensaver-command', '-lock'])
    else:
        print('Only locking is supported. Recieved', command, file=sys.stderr)
        return


mqtt_client = paho.mqtt.client.Client()
# NOTE: The will must be set before connecting.
mqtt_client.will_set(topic=AVAILABILITY_TOPIC, payload='offline')

# FIXME: Try anonymous, and fallback on guest:guest when that fails
mqtt_client.username_pw_set(username='guest', password='guest')
connect_srv(mqtt_client)
mqtt_client.loop_start()

# FIXME: Notify Systemd that we're ready
state_topic, command_topic = mqtt_discovery(mqtt_client)

mqtt_client.message_callback_add(sub=command_topic, callback=command_callback)
mqtt_client.subscribe(topic=command_topic)

# FIXME: run 'xscreensaver-command -time' once to get the initial state:
#            XScreenSaver 6.06: screen non-blanked since Tue Jul  9 16:42:18 2024
#            XScreenSaver 6.06: screen blanked since Tue Jul  9 16:42:32 2024
#            XScreenSaver 6.06: screen locked since Tue Jul  9 16:42:08 2024

xscreensaver_watch = subprocess.Popen(['xscreensaver-command', '-watch'], stdout=subprocess.PIPE, text=True)
for xscreensaver_event in xscreensaver_watch.stdout:
    event, timestamp = xscreensaver_event.strip().split(maxsplit=1)
    print(event, timestamp)
    if event in EVENT_TO_MQTT:
        # Ping the availability topic every time because HA can restarted and forget the latest state
        # Send new/current state to HA
        mqtt_client.publish(topic=AVAILABILITY_TOPIC, payload='online', retain=False)
        mqtt_client.publish(topic=state_topic,
                            payload=EVENT_TO_MQTT[event],
                            retain=False)
