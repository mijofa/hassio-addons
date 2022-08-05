#!/command/with-contenv bash

set -eEu -o pipefail
shopt -s failglob
trap 'bashio::log.info "${BASH_SOURCE:-$0}:${LINENO}: unknown error" >&2' ERR

CONFIG_PATH=/data/options.json


echo "Checking Pulseaudio sink..."
if pactl list sinks | grep -q 'mijofa.snapcast-proxy = ' ; then
    echo "  fifo sink already exists, skipping."
else
    echo "  loading fifo-sink module."
    pactl load-module module-pipe-sink file=/data/external/snapfifo sink_name=snapfifo format=s16le rate=48000 sink_properties="device.description='Snapcast\ FIFO'device.icon_name='mdi:cast-audio'mijofa.snapcast-proxy='$(date -Iseconds)'"
fi

echo "Writing snapserver.conf..."
# FIXME: Why the fuck can't I make bashio::config work?!?!
cat >/etc/snapserver.conf <<EOF
[server]
threads = $(jq --raw-output -c -M '.server_threads' /data/options.json)
datadir = $(jq --raw-output -c -M '.server_datadir' /data/options.json)

[stream]
$(jq --raw-output -c -M '.stream_sources[] | "source = \(.)"' /data/options.json)
sampleformat = $(jq --raw-output -c -M '.stream_sampleformat' /data/options.json)
codec = $(jq --raw-output -c -M '.stream_codec' /data/options.json)
chunk_ms = $(jq --raw-output -c -M '.stream_chunk_ms' /data/options.json)
buffer = $(jq --raw-output -c -M '.stream_buffer' /data/options.json)
send_to_muted = $(jq --raw-output -c -M '.stream_send_to_muted' /data/options.json)

[http]
enabled = $(jq --raw-output -c -M '.http_enabled' /data/options.json)
doc_root = /usr/share/snapserver/snapweb/

[tcp]
enabled = $(jq --raw-output -c -M '.tcp_enabled' /data/options.json)

[logging]
sink = stderr
filter = $(jq --raw-output -c -M '.logging_filter' /data/options.json)
EOF

printf 'Telling HA to reload audio config: %s\n' \
    "$(curl --silent --data '{}' -H "Authorization: Bearer $SUPERVISOR_TOKEN" http://supervisor/audio/reload)"

echo "Starting Snapserver."
exec /usr/bin/snapserver -c /etc/snapserver.conf
