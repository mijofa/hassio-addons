#!/usr/bin/python3
"""Connect screensaver state to Home Assistant."""
import sys
import os
import pathlib
import dns.resolver
import json
import socket
import subprocess
import uuid
import typing

import pyotp

import paho.mqtt.client
import dbus
from gi.repository import GLib
from dbus.mainloop.glib import DBusGMainLoop

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

MQTT_TOPIC_BASE = f"homeassistant/lock/{socket.gethostname()}/screensaver"
AVAILABILITY_TOPIC = '/'.join((MQTT_TOPIC_BASE, "availability"))



def mqtt_discovery(mqtt_client):
    """Send MQTT discovery info for Home Assistant."""
    # FIXME: Why do the DLNA & Nmap devices combine into one, but I can't make this combine with them?
    mac_address = f'{uuid.getnode():02x}'
    unique_id = ':'.join(mac_address[i:i + 2] for i in range(0, len(mac_address), 2))

    state_topic = '/'.join((MQTT_TOPIC_BASE, "state"))
    attributes_topic = '/'.join((MQTT_TOPIC_BASE, "attributes"))
    command_topic = '/'.join((MQTT_TOPIC_BASE, "command"))

    mqtt_client.publish(topic='/'.join((MQTT_TOPIC_BASE, "config")),
                        payload=json.dumps({
                            "availability_topic": AVAILABILITY_TOPIC,
                            "device": {
                                "connections": [("mac", unique_id)],
                                "name": socket.gethostname()},
                            "unique_id": f'screensaver_mqtt:{uuid.getnode():02x}',
                            # "category": "config/diagnostic",  # FIXME: wtf is this?
                            "icon": "mdi:monitor-lock",
                            # FIXME: Not currently sending attributes anywhere
                            "json_attributes_topic": attributes_topic,
                            "name": "Screensaver",
                            "state_topic": state_topic,
                            "command_topic": command_topic,
                            "command_template": '{{ value }}{% if code is not none %} {{ code }}{% endif %}',
                            "code_format": r"^(\d+|.+)?$",
                            "retain": False,  # Tells Home Assistant to NOT mark commands for retainment in mqtt
                        }),
                        retain=True)

    return state_topic, command_topic


def command_callback(client, unknown, message):
    if message.topic != command_topic:
        raise Exception("Callback called from the wrong topic")
    command = message.payload.decode().split()
    print('mqtt>', command[0] if len(command) == 1 else f'{command[0]} [REDACTED]', flush=True)
    if command[0] == 'LOCK':
        # FIXME: Should I do anything if a code is provided here?
        # FIXME: '1' is a magic number for the "first" session, how do we avoid this?
        return login1_manager.LockSession('1')
    if command[0] == 'UNLOCK':
        # FIXME: '1' is a magic number for the "first" session, how do we avoid this?
        if totp is None:
            # Raising an exception here would kill the mqtt client, we don't want that
            print(NotImplementedError("TOTP not setup, can't unlock via MQTT"), file=sys.stderr, flush=True)
            return login1_manager.ActivateSession('1')
        elif totp is not None and len(command) == 1:
            # Raising an exception here would kill the mqtt client, we don't want that
            # FIXME: This exception type is wrong?
            print(NotImplementedError("Can't unlock without providing an unlock code"), file=sys.stderr, flush=True)
            return login1_manager.ActivateSession('1')
        elif totp is not None and len(command) == 2 and command[1].isdigit():
            # FIXME: Put more effort into tuning valid_window, or make it configurable
            # NOTE: Must remain a str despite 'isdigit' above, because the leading 0s are relevant
            if totp.verify(command[1], valid_window=1):
                print('Correct OTP code provided, unlocking', flush=True)
                return login1_manager.UnlockSession('1')
            else:
                # Raising an exception here would kill the mqtt client, we don't want that
                print("WARNING: Incorrect OTP provided, ignoring", file=sys.stderr, flush=True)
                return
        else:
            # Raising an exception here would kill the mqtt client, we don't want that
            print("Incorrect unlock instruction provided, ignoring", file=sys.stderr, flush=True)
            return
    else:
        print('Unsupported command recieved:', command, file=sys.stderr, flush=True)
        return

global totp
if 'CREDENTIALS_DIRECTORY' in os.environ:
    totp = pyotp.parse_uri((pathlib.Path(os.environ.get('CREDENTIALS_DIRECTORY')) / pathlib.Path('otpauth_uri')).read_text())
else:
    totp = None
    # import pyotp, socket; pyotp.TOTP(s=pyotp.random_base32(), issuer='mijofa/logind-mqtt.py', name=socket.gethostname()).provisioning_uri()
    print("You should setup totp...", file=sys.stderr)


mqtt_client = paho.mqtt.client.Client(callback_api_version=paho.mqtt.client.CallbackAPIVersion.VERSION2)
# NOTE: The will must be set before connecting.
mqtt_client.will_set(topic=AVAILABILITY_TOPIC, payload='offline')

# FIXME: Try anonymous, and fallback on guest:guest when that fails
mqtt_client.username_pw_set(username='guest', password='guest')
mqtt_client.connect_srv()
# mqtt_client.loop_start()

# FIXME: Notify Systemd that we're ready
state_topic, command_topic = mqtt_discovery(mqtt_client)

mqtt_client.message_callback_add(sub=command_topic, callback=command_callback)
mqtt_client.subscribe(topic=command_topic)

DBusGMainLoop(set_as_default=True)
loop = GLib.MainLoop()


## Bypass paho.mqtt.client's loop and use GLib's instead
def loop_mqtt_read(socket, condition):
    assert socket == mqtt_client.socket()
    assert condition == GLib.IO_IN
    mqtt_client.loop_read()
    return True
def loop_mqtt_regularly():
    if mqtt_client.want_write():
        print("Running loop_write", flush=True)
        mqtt_client.loop_write()
    mqtt_client.loop_misc()
    return True
GLib.io_add_watch(mqtt_client.socket(), GLib.IO_IN, loop_mqtt_read)
GLib.idle_add(loop_mqtt_regularly)


bus = dbus.SystemBus()
login1 = bus.get_object("org.freedesktop.login1", "/org/freedesktop/login1")
login1_manager = dbus.Interface(login1, "org.freedesktop.login1.Manager")

# # FIXME: WTF couldn't I make this see changes to LockedHint?
# def f(interface: str, changed_properties: dict[str, typing.Any], invalidated_properties: list[str]):
#     assert interface.startswith('org.freedesktop.login1')
#     IdleHint: bool | None = None
#     if 'IdleHint' in changed_properties:
#         IdleHint = bool(changed_properties['IdleHint'])
#     elif 'IdleHint' in invalidated_properties:
#         IdleHint = False
#     # Remind the mqtt server we're still here, and providing accurate info
#     mqtt_client.publish(topic=AVAILABILITY_TOPIC, payload='online', retain=False)
#     # Tell the mqtt server about our lock state
#     if IdleHint is not None:
#         mqtt_client.publish(topic=state_topic,
#                             # FIXME: Add 'LOCKING' during blanking
#                             # FIXME: Add 'UNLOCKING' when unblanked, before unlocked?
#                             payload='LOCKED' if IdleHint else 'UNLOCKED',
#                             retain=False)
#
# login1.connect_to_signal(signal_name='PropertiesChanged', handler_function=f, dbus_interface='org.freedesktop.DBus.Properties')

IdleHint: bool | None = None
LockedHint: bool | None = None


def handle_dbus_property_update(interface: str,
                                changed_properties: dict[str, typing.Any],
                                invalidated_properties: list[str],
                                sender_path: str):
    if interface != 'org.freedesktop.login1.Session':
        # We don't do actually care, but for some reason we couldn't make add_signal_receiver match for this specifically
        return
    assert sender_path.startswith('/org/freedesktop/login1/session'), sender_path

    global IdleHint, LockedHint
    if 'IdleHint' in changed_properties:
        IdleHint = bool(changed_properties['IdleHint'])
    elif 'IdleHint' in invalidated_properties:
        # I've never actually seen this be invalidated, so I don't think this is possible
        IdleHint = None
    if 'LockedHint' in changed_properties:
        LockedHint = bool(changed_properties['LockedHint'])
    elif 'LockedHint' in invalidated_properties:
        # I've never actually seen this be invalidated, so I don't think this is possible
        LockedHint = None

    if LockedHint == True and IdleHint == False and 'LockedHint' in changed_properties:
        # Locked before screen blanked? User pressed Super+L to lock the screen
        payload = 'LOCKING'
    # elif LockedHint == True and IdleHint == False and 'IdleHint' in changed_properties:
    #     # Screen unblanked while locked? User probably pressed a button, or a notification came in
    #     payload = 'UNLOCKING'
    elif LockedHint == True:
        payload = 'LOCKED'
    elif LockedHint == False and IdleHint == True and 'LockedHint' not in changed_properties:
        # Screen blanked before locked? Idle timeout occurred, we're about to lock
        payload = 'LOCKING'
    elif LockedHint == False:
        payload = 'UNLOCKED'
    else:
        payload = None

    print(f"{payload}: IDLE={IdleHint}, LOCKED={LockedHint}, CHANGED={[str(k) for k in changed_properties.keys()]}", flush=True)

    if payload is not None:
        # Remind the mqtt server we're still here, and providing accurate info
        mqtt_client.publish(topic=AVAILABILITY_TOPIC, payload='online', retain=False)
        mqtt_client.publish(topic=state_topic,
                            payload=payload,
                            retain=False)
    else:
        # We're confused right now, tell Home Assistant that the state is unreliable
        # FIXME: Use 'MOTOR_JAMMED' or 'MOTOR_OK' instead?
        mqtt_client.publish(topic=AVAILABILITY_TOPIC, payload='offline', retain=False)


# FIXME: WTF couldn't I make this work with login1.connect_to_signal?
bus.add_signal_receiver(handler_function=handle_dbus_property_update,
                        dbus_interface='org.freedesktop.DBus.Properties',
                        signal_name='PropertiesChanged',
                        path_keyword='sender_path')

loop.run()
