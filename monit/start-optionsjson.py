#!/usr/bin/python3
"""Small wrapper for the base upstream startup script to read config from Home Assistant's /data/options.json."""
import json
import os
import pathlib
import sys

OPTIONS_FILE = pathlib.Path('/data/options.json')
CONFIG_FILE = pathlib.Path('/data/monitrc')

if not OPTIONS_FILE.exists():
    raise Exception("No /data/options.json file")

HA_options = json.loads(OPTIONS_FILE.read_text())

application_conf = HA_options['monitrc'].format(**HA_options, SUPERVISOR_TOKEN=os.environ.get('SUPERVISOR_TOKEN'))

if __name__ == "__main__":
    print("Overwriting monitrc with custom config", flush=True)

    # Ensure the CONFIG_FILE is created with '-r--------' perms
    # Monit refuses to start with anything more permissive than 0700
    os.umask(0o377)

    CONFIG_FILE.write_text(application_conf)
    os.execv('/usr/local/bin/monit', ['monit', '-I', '-c', CONFIG_FILE])
