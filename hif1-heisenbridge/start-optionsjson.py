#!/usr/bin/python3
"""Small wrapper for the base upstream startup script to read config from Home Assistant's /data/options.json."""
import json
import pathlib
# import secrets
import socket
import subprocess
import sys

import yaml

OPTIONS_FILE = pathlib.Path('/data/options.json')
REGISTRATION_FILE = (pathlib.Path('/share/matrix_appservices/') / socket.gethostname()).with_suffix('.yaml')

if not OPTIONS_FILE.exists():
    raise Exception("No /data/options.json file")

HA_options = json.loads(OPTIONS_FILE.read_text())

heisenbridge_args = ['--config', str(REGISTRATION_FILE), '--listen-address', '0.0.0.0',
                     '--owner', HA_options['heisenbridge_owner_mxid'], HA_options['heisenbridge_synapse_url']]

if __name__ == "__main__":
    # Generate registration.yaml if it doesn't already exist
    if not REGISTRATION_FILE.exists():
        print("Overwriting registration yaml.", flush=True)
        subprocess.check_call(['heisenbridge', '--generate', *heisenbridge_args])
        registration_yaml = yaml.safe_load(REGISTRATION_FILE.read_text())
        registration_yaml['url'] = HA_options['heisenbridge_own_url']
        REGISTRATION_FILE.write_text(yaml.dump(registration_yaml))
        print("Appservice registration yaml generated, go sort out registration before restarting this addon.",
              file=sys.stderr, flush=True)
    else:
        print('Starting Heisenbridge with command:', ['heisenbridge', *heisenbridge_args], flush=True)
        heisenbridge = subprocess.check_call(['heisenbridge', *heisenbridge_args])
