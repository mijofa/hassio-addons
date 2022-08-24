#!/usr/bin/python3
"""Small wrapper for the base upstream startup script to read config from Home Assistant's /data/options.json."""
import json
# import os
import pathlib
# import secrets
import subprocess
import sys

import yaml

OPTIONS_FILE = pathlib.Path('/data/options.json')
REGISTRATION_FILE = pathlib.Path('/share/matrix_appservices/hif1-heisenbridge_wireguard.yaml')

if not OPTIONS_FILE.exists():
    raise Exception("No /data/options.json file")

HA_options = json.loads(OPTIONS_FILE.read_text())

heisenbridge_args = ['--config', str(REGISTRATION_FILE), '--owner', HA_options['owner_mxid'], HA_options['synapse_url']]

if __name__ == "__main__":
    # Generate registration.yaml if it doesn't already exist
    if not REGISTRATION_FILE.exists():
        print("Overwriting registration yaml.", flush=True)
        subprocess.check_call(['heisenbridge', '--generate', *heisenbridge_args])
        registration_yaml = yaml.safe_load(REGISTRATION_FILE.read_text())
        registration_yaml['url'] = HA_options['own_url']
        REGISTRATION_FILE.write_text(yaml.dump(registration_yaml))

    subprocess.check_call(['heisenbridge', *heisenbridge_args, *sys.argv[1:]])
