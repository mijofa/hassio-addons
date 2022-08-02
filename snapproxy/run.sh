#!/usr/bin/env bashio

set -eEu -o pipefail
shopt -s failglob
trap 'bashio::log.info "${BASH_SOURCE:-$0}:${LINENO}: unknown error"' ERR

bashio::log.info "Copying snapweb file snapcontrol.js:"
cp /usr/share/snapserver/snapweb/snapcontrol.js /share/
bashio::log.info "Copying snapweb file snapstream.js:"
cp /usr/share/snapserver/snapweb/snapstream.js /share/
bashio::log.info "Writing snapserver.conf..."
# Convert the json options file into Snapserver's .ini config format
jq -r 'def kv: to_entries[] | if .key=="sources" then .value|split(" ")|to_entries[]|"source = \(.value)" else "\(.key) = \(.value)" end; to_entries[] | "[\(.key)]", (.value|kv)' /data/options.json >/etc/snapserver.conf

bashio::log.info "Starting SnapServer..."
/usr/bin/snapserver -c /etc/snapserver.conf
