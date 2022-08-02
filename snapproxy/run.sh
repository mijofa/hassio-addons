#!/usr/bin/env bashio

set -eEu -o pipefail
shopt -s failglob
trap 'bashio::log.info "${BASH_SOURCE:-$0}:${LINENO}: unknown error"' ERR

config=/etc/snapserver.conf

if ! bashio::fs.file_exists '/etc/snapserver.conf'; then
    touch /etc/snapserver.conf ||
        bashio::exit.nok "Could not create snapserver.conf file on filesystem"
fi
bashio::log.info "Populating snapserver.conf..."

bashio::log.info "WTF!? $(ls /)"
bashio::log.info "WTF!? $(cat /data/options.json)"

# Start creation of configuration

bashio::log.info "What is all of the config? $(bashio::api.supervisor GET '/addons/self/options/config' false)"
bashio::log.info "Or maybe it's just the first time we read the config $(bashio::config 'stream')"
echo "[stream]" > "${config}"
bashio::log.info "looping"
for stream in $(bashio::config 'stream.sources') ; do # |sed "s/\$UPSTREAM_SNAPSERVER/$(bashio::config 'upstream_snapserver')/g"); do
    bashio::log.info "stream... $stream"
    echo "source = ${stream}" >> "${config}"
done
bashio::log.info "buffer... $(bashio::config 'stream.buffer')"
echo "buffer = $(bashio::config 'stream.buffer')" >> "${config}"
bashio::log.info "codec..."
echo "codec = $(bashio::config 'stream.codec')" >> "${config}"
bashio::log.info "send_to_muted..."
echo "send_to_muted = $(bashio::config 'stream.send_to_muted')" >> "${config}"
bashio::log.info "sampleformat..."
echo "sampleformat = $(bashio::config 'stream.sampleformat')" >> "${config}"

echo "[http]" >> "${config}"
echo "enabled = $(bashio::config 'http.enabled')" >> "${config}"
echo "doc_root = $(bashio::config 'http.doc_root')" >> "${config}"

echo "[tcp]" >> "${config}"
echo "enabled = $(bashio::config 'tcp.enabled')" >> "${config}"

echo "[logging]" >> "${config}"
echo "logsink = stderr"

echo "[server]" >> "${config}"
echo "threads = $(bashio::config 'server.threads')" >> "${config}"

echo "[server]" >> "${config}"
datadir=$(bashio::config 'server.datadir')
mkdir -p "$datadir"
echo "datadir = $datadir" >> "${config}"

bashio::log.info "Starting SnapServer..."

/usr/bin/snapserver -c /etc/snapserver.conf
