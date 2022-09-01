#!/usr/bin/with-contenv bash

set -eEu -o pipefail
shopt -s failglob
trap 'bashio::log.info "${BASH_SOURCE:-$0}:${LINENO}: unknown error" >&2' ERR


echo "Checking Pulseaudio sink..."
if pactl list sinks | grep -q 'mijofa.snapcast-proxy = ' ; then
    echo "  fifo sink already exists, skipping."
else
    echo "  loading fifo-sink module."
    pactl load-module module-pipe-sink file=/data/external/snapfifo sink_name=snapfifo format=s16le rate=48000 sink_properties="device.description='Snapcast\ FIFO'device.icon_name='mdi:cast-audio'mijofa.snapcast-proxy='$(date -Iseconds)'"
fi

printf 'Telling HA to reload audio config: %s\n' \
    "$(curl --silent --data '{}' -H "Authorization: Bearer $SUPERVISOR_TOKEN" http://supervisor/audio/reload)"
