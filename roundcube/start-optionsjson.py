#!/usr/bin/python3
"""Small wrapper for the base upstream startup script to read config from Home Assistant's /data/options.json."""
import json
import os
import pathlib
# import secrets
import subprocess
import sys
import urllib.parse
import urllib.request

OPTIONS_FILE = pathlib.Path('/data/options.json')

# I've symlinked some Roundcube directories into /data, but now Roundcube expects them to exist first
# FIXME: Is it safe to just symlink them to /data directly?
CONFIG_DIR = pathlib.Path('/data/config')
DB_DIR = pathlib.Path('/data/db')


def parse_dburl_for_roundcube(url: str):
    """Parse URL string into a set of env vars for Roundcube."""
    # FIXME: This could probably be a generator
    parsed_url = urllib.parse.urlparse(url)
    return {
        'ROUNDCUBEMAIL_DB_TYPE': 'pgsql' if parsed_url.scheme == 'postgres' else parsed_url.scheme if parsed_url.scheme else None,
        'ROUNDCUBEMAIL_DB_HOST': parsed_url.hostname if parsed_url.hostname else None,
        'ROUNDCUBEMAIL_DB_PORT': parsed_url.port if parsed_url.port else None,
        'ROUNDCUBEMAIL_DB_USER': parsed_url.username if parsed_url.username else None,
        'ROUNDCUBEMAIL_DB_PASSWORD': parsed_url.password if parsed_url.password else None,
        'ROUNDCUBEMAIL_DB_NAME': parsed_url.path.strip('/') if parsed_url.path else None,
    }


if not OPTIONS_FILE.exists():
    raise Exception("No /data/options.json file")

HA_options = json.loads(OPTIONS_FILE.read_text())

roundcube_env = HA_options['roundcube']
if roundcube_env['database_url']:
    roundcube_env.update(parse_dburl_for_roundcube(roundcube_env['database_url']))

# Remove empty variables so that it lets the defaults happen rather than treating them as empty strings
for k, v in list(roundcube_env.items()):
    if not v:
        roundcube_env.pop(k)

if __name__ == "__main__":
    if not DB_DIR.exists():
        DB_DIR.mkdir()
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir()

    roundcube_args = ["/docker-entrypoint.sh", sys.argv[1] if len(sys.argv) >= 2 else "apache2-foreground", *sys.argv[2:]]
    print('Starting Roundcube with command:', roundcube_args, flush=True)
    subprocess.check_call(roundcube_args, env={**os.environ, **roundcube_env})
