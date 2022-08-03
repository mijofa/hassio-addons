#!/usr/bin/env bashio

set -eEu -o pipefail
shopt -s failglob
trap 'bashio::log.info "${BASH_SOURCE:-$0}:${LINENO}: unknown error"' ERR

CONFIG_PATH=/data/options.json


bashio::log.info "writing snapserver.conf..."
# # Convert the json options file into Snapserver's .ini config format
# jq -r 'def kv: to_entries[] | if .key=="sources" then .value|split(" ")|to_entries[]|"source = \(.value)" else "\(.key) = \(.value)" end; to_entries[] | "[\(.key)]", (.value|kv)' /data/options.json >/etc/snapserver.conf

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

bashio::log.info "Starting SnapServer..."
/usr/bin/snapserver -c /etc/snapserver.conf
