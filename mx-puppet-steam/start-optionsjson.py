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
CONFIG_FILE = pathlib.Path('/data/config.yaml')
REGISTRATION_FILE = pathlib.Path('/data/steam-registration.yaml')
REGISTRATIONS_DIR = pathlib.Path('/share/matrix_appservices')

if not OPTIONS_FILE.exists():
    raise Exception("No /data/options.json file")

HA_options = json.loads(OPTIONS_FILE.read_text())

# Reading this in as YAML to dump it back out is unnecessary, but doesn't hurt, and might make YAML syntax errors more obvious
application_conf = yaml.safe_load(HA_options['config.yaml'].format(**HA_options))

if __name__ == "__main__":
    print("Overwriting config.yaml with custom config", flush=True)
    CONFIG_FILE.write_text(yaml.dump(application_conf))
    if not REGISTRATION_FILE.exists():
        # Appservice registration file has not been created, this is probably the first run.
        # So let's generate it and copy it somewhere Synapse can find it.
        subprocess.check_call(['/opt/mx-puppet-steam/docker-run.sh'])
        assert REGISTRATION_FILE.exists()
        if not REGISTRATIONS_DIR.is_dir():
            REGISTRATIONS_DIR.mkdir()

        # FIXME: Should I be regularly updating this?
        (REGISTRATIONS_DIR / 'mx-puppet-steam.yaml').write_text(REGISTRATION_FILE.read_text())
        print("Appservice registration yaml generated, go sort out registration before restarting this addon.",
              file=sys.stderr, flush=True)
    else:
        # Start normally
        print("Starting service", flush=True)
        subprocess.check_call(['/opt/mx-puppet-steam/docker-run.sh'])
