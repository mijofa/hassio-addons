#!/usr/bin/python3
"""Small wrapper for the base upstream startup script to read config from Home Assistant's /data/options.json."""
import json
import os
import pathlib
# import secrets
import subprocess
import sys
import urllib.parse

OPTIONS_FILE = pathlib.Path('/data/options.json')

DATA_DIR = pathlib.Path('/data/hm3')


def parse_dburl(url: str):
    """Parse URL string into a set of env vars for Roundcube."""
    # FIXME: This could probably be a generator
    parsed_url = urllib.parse.urlparse(url)
    return {
        'CYPHT_DB_DRIVER': 'pgsql' if parsed_url.scheme == 'postgres' else parsed_url.scheme if parsed_url.scheme else None,
        'CYPHT_DB_HOST': parsed_url.hostname if parsed_url.hostname else None,
        'CYPHT_DB_PORT': parsed_url.port if parsed_url.port else None,
        'CYPHT_DB_NAME': parsed_url.path.strip('/') if parsed_url.path else None,
        'CYPHT_DB_USER': parsed_url.username if parsed_url.username else None,
        'CYPHT_DB_PASS': parsed_url.password if parsed_url.password else None,
    }


if not OPTIONS_FILE.exists():
    raise Exception("No /data/options.json file")

HA_options = json.loads(OPTIONS_FILE.read_text())

# Remove empty variables to let the defaults happen rather than treating them as empty strings
for k, v in list(HA_options.items()):
    if not v:
        HA_options.pop(k)


cypht_env = {k: v for k, v in HA_options.items() if k.startswith('CYPHT_')}
if cypht_env.get('CYPHT_DB_URL'):
    cypht_env.update(parse_dburl(cypht_env.pop('CYPHT_DB_URL')))

if __name__ == "__main__":
    if not DATA_DIR.exists():
        DATA_DIR.mkdir()

    cypht_args = ["docker-entrypoint.sh", sys.argv[1] if len(sys.argv) >= 2 else "php-fpm", *sys.argv[2:]]
    print('Starting cypht with env:', cypht_env, flush=True)
    subprocess.check_call(cypht_args, env={**os.environ, **cypht_env})
