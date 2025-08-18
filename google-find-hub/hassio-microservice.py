import json
import asyncio
import pathlib

import paho.mqtt.client

from NovaApi.ListDevices.nbe_list_devices import request_device_list
from ProtoDecoders.decoder import parse_device_update_protobuf
from NovaApi.ExecuteAction.LocateTracker.location_request import create_location_request
from NovaApi.nova_request import nova_request
from NovaApi.scopes import NOVA_ACTION_API_SCOPE
from NovaApi.util import generate_random_uuid
from Auth.fcm_receiver import FcmReceiver
from NovaApi.ExecuteAction.LocateTracker.decrypt_locations import extract_locations
from ProtoDecoders import DeviceUpdate_pb2


reported_devices: set[str] = set()


async def list_devices():
    result_hex = request_device_list()

    # parse_device_list_protobuf
    device_list = DeviceUpdate_pb2.DevicesList()
    device_list.ParseFromString(bytes.fromhex(result_hex))

    # get_canonic_ids
    for device in device_list.deviceMetadata:
        if device.identifierInformation.type == DeviceUpdate_pb2.IDENTIFIER_ANDROID:
            # Android devices notify the user every time we query Find Hub, this is annoying.
            # Note we aren't trying to hide our tracking from the user,
            # but we are tracking this constantly which would make those notifications useless.
            # If someone else queries the Android device location via Find Hub we want to know.
            # We can track Android devices via other means anyway (such as Home Assistant app)
            continue
            canonic_ids = device.identifierInformation.phoneInformation.canonicIds.canonicId
        else:
            canonic_ids = device.identifierInformation.canonicIds.canonicId
        for canonic_id in canonic_ids:  # Can a single device have more than one ID?
            if canonic_id.id not in reported_devices:
                mqtt_discovery(id=canonic_id.id,
                               device=device)
                reported_devices.add(canonic_id.id)
            yield {'type': device.identifierInformation.type,
                   'name': device.userDefinedDeviceName,
                   'id': canonic_id.id}


def location_update_handler(resp_hex):
    update = parse_device_update_protobuf(resp_hex)
    # print(device_name, f"({', '.join(canonic_id.id for canonic_id in update.deviceMetadata.identifierInformation.canonicIds.canonicId)})",
    #       device_image if device_image else '',
    #       _get_latest_location(extract_locations(update)))
    for canonic_id in update.deviceMetadata.identifierInformation.canonicIds.canonicId:
        data: dict[str, str | int | bool] = _get_latest_location(extract_locations(update))
        data['gps_accuracy'] = data.pop('accuracy')  # Home Assistant requires different key name
        mqtt_client.publish(
            topic='/'.join((MQTT_TOPIC_BASE, canonic_id.id, "attributes")),
            payload=json.dumps(data),
        )


def _get_latest_location(locations):
    with_coords = [l for l in locations if 'latitude' in l and 'longitude' in l]
    if not with_coords:
        return None
    return max(with_coords, key=lambda l: l.get('time', 0))


async def send_new_location_requests(fcm_token):
    # FIXME: Does the Google API support just requesting "all" devices?
    async for device in list_devices():
        request_uuid = generate_random_uuid()
        # FIXME: Record this UUID so we can ignore requests we didn't make ourselves?
        payload = create_location_request(device['id'], fcm_token, request_uuid)
        nova_request(NOVA_ACTION_API_SCOPE, payload)



### MQTT stuff!

MQTT_TOPIC_BASE: str = "homeassistant/device_tracker/google-find-hub"
AVAILABILITY_TOPIC: str = '/'.join((MQTT_TOPIC_BASE, "availability"))


def mqtt_discovery(id: str, device):
    """Send MQTT discovery info for Home Assistant."""
    mqtt_client.publish(
        topic='/'.join((MQTT_TOPIC_BASE, id, "config")),
        payload=json.dumps({
            "platform": "device_tracker",
            "source_type": "bluetooth_le",  # FIXME: Depends on device type!
            "device": {
                "name": "Google Find Hub",
                "manufacturer": device.information.deviceRegistration.manufacturer,
                "model": device.information.deviceRegistration.model,
                "model_id": device.information.deviceRegistration.fastPairModelId,
                "identifiers": [canonic_id.id for canonic_id in device.identifierInformation.canonicIds.canonicId],
                "connections": [('service', 'https://android.com/find'),
                                *[('email', info.email) for info in device.information.accessInformation]]
            },
            # FIXME: We need to actually use this availability topic
            "availability_topic": AVAILABILITY_TOPIC,
            # "category": "config/diagnostic",  # FIXME: wtf is this?
            # "icon": "mdi:monitor-speaker",
            "json_attributes_topic": '/'.join((MQTT_TOPIC_BASE, id, "attributes")),
            "name": device.userDefinedDeviceName,
            # "state_topic": '/'.join((MQTT_TOPIC_BASE, id, "state")),
            "unique_id": f'google-find-hub_{id}',
        }),
    )


if __name__ == '__main__':
    if not pathlib.Path('/data/secrets.json').exists():
        # FIXME: Provide some instructions, anything at all
        print("No secrets found, go fix")
        exit(2)

    config: dict[str, str | int | bool] = json.loads(pathlib.Path('/data/options.json').read_text())

    polling_interval: int = config['polling_interval_mins']

    global mqtt_client
    mqtt_client = paho.mqtt.client.Client(
        # We don't actually use these callbacks at all (yet?)
        # but there's a deprecation warning if I don't set this.
        callback_api_version=paho.mqtt.client.CallbackAPIVersion.VERSION2)
    # NOTE: The will must be set before connecting.
    mqtt_client.will_set(topic=AVAILABILITY_TOPIC, payload='offline')
    # FIXME: Try anonymous, and fallback on guest:guest when that fails
    mqtt_client.username_pw_set(username='guest', password='guest')
    mqtt_client.connect_async(host=config['mqtt_host'], port=config['mqtt_port'])
    mqtt_client.loop_start()
    mqtt_client.will_set(topic=AVAILABILITY_TOPIC, payload="offline")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    fcm = FcmReceiver()
    loop.run_until_complete(fcm._register_for_fcm_and_listen())
    fcm_token = fcm.register_for_location_updates(location_update_handler)

    # NOTE: Google remembers these requests across runs.
    #       So if you Ctrl-C and rerun, you may start seening extra results,
    #       this is normal as it is showing you results from the previous run.
    # FIXME: Can we confirm every device responds before we request again?
    while True:
        mqtt_client.publish(topic=AVAILABILITY_TOPIC, payload="online")
        loop.run_until_complete(asyncio.gather(
            send_new_location_requests(fcm_token=fcm_token),
            asyncio.sleep(delay=60 * polling_interval),
        ))

    # This should never be reached.
    pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()
