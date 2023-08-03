#!/bin/ash

# Get currently connected MACs
# Use this to initialise the current state of things immediately before we start watching for changes
# FIXME: Can we check this **after** we start watching for changes?
wifi_clients="$(for nic in $(iw dev | sed --quiet '/^\s\+Interface\s/ s///p') ; do
                    iw dev $nic station dump
                done | sed --quiet '/^Station\s\([[:xdigit:]:]\+\)\(\s(.*)\)\?$/ s//\1/p')"

# Is Muir (Mike's phone) in the list of connected clients
echo "$wifi_clients" | grep -qFx '2a:e0:9b:0d:0e:1e'
# Is Gaby's phone in list of connected clients
# FIXME: Is this Gaby's MAC?
echo "$wifi_clients" | grep -qFx '5e:0c:a4:36:ae:81'


# Muir's discovery info example
# NOTE: By ensuring all "device" dicts are identical, we can have all the entities grouped in the same device
# NOTE: I don't really like that I'm using the "NFC" icon, but the "wireless" one looks shit.
#       'mdi:router-wireless' is probably a decent default if not doing unique icons for each device.
#       I'm using 'mdi:cellphone-message' for Gaby
# ref: https://www.home-assistant.io/integrations/device_tracker.mqtt/#using-the-discovery-protocol
# topic: homeassistant/device_tracker/mijofa-iw2mqtt/2a-e0-9b-0d-0e-1e/config
# { "state_topic": "mijofa-iw2mqtt/2a-e0-9b-0d-0e-1e",
#   "device": {
#     "connections": [
#         ["mac", "2a:e0:9b:0d:0e:1e"],
#         ["mac", "5e:0c:a4:36:ae:81"]
#     ],
#     "name": "OpenWRT WiFi Devices"
#   },
#   "name": "muir",
#   "icon": "mdi:mdi:router-wireless",
#   "unique_id": "mijofa-iw2mqtt.2a-e0-9b-0d-0e-1e",
#   "source_type": "router"
# }
# And for Gaby's
# topic: homeassistant/device_tracker/mijofa-iw2mqtt/5e-0c-a4-36-ae-81/config
# { "state_topic": "mijofa-iw2mqtt/5e-0c-a4-36-ae-81",
#   "device": {
#     "connections": [
#         ["mac", "2a:e0:9b:0d:0e:1e"],
#         ["mac", "5e:0c:a4:36:ae:81"]
#     ],
#     "name": "OpenWRT WiFi Devices"
#   },
#   "name": "gaby's phone",
#   "icon": "mdi:mdi:router-wireless",
#   "unique_id": "mijofa-iw2mqtt.5e-0c-a4-36-ae-81",
#   "source_type": "router"
# }
