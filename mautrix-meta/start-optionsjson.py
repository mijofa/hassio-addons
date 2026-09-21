#!/usr/bin/python3
"""Small wrapper for the base upstream startup script to read config from Home Assistant's /data/options.json."""
import json
# import os
import pathlib
# import secrets
import subprocess
import sys
import time

import yaml

OPTIONS_FILE = pathlib.Path('/data/options.json')
CONFIG_FILE = pathlib.Path('/data/config.yaml')
CONFIG_FILE_BACKUP = pathlib.Path('/data/config.yaml~')
REGISTRATION_FILE = pathlib.Path('/data/registration.yaml')
REGISTRATIONS_DIR = pathlib.Path('/share/matrix_appservices')

if not OPTIONS_FILE.exists():
    raise FileNotFoundError("No /data/options.json file")

HA_options = json.loads(OPTIONS_FILE.read_text())

# Get the as & hs tokens directly from the registation yaml file used by Synapse
if REGISTRATION_FILE.exists():
    registration_conf = yaml.safe_load(REGISTRATION_FILE.read_text())
    HA_options['as_token'] = registration_conf['as_token']
    HA_options['hs_token'] = registration_conf['hs_token']
else:
    HA_options['as_token'] = "This value is generated when generating the registration"
    HA_options['hs_token'] = "This value is generated when generating the registration"

# Reading this in as YAML to dump it back out is unnecessary, but doesn't hurt, and might make YAML syntax errors more obvious
application_conf = yaml.safe_load(HA_options['config.yaml'].format(**HA_options))

if __name__ == "__main__":
    print("Overwriting config.yaml with custom config", flush=True)
    config_file_contents_new = yaml.dump(application_conf)
    config_file_contents_old = CONFIG_FILE.read_text()
    if CONFIG_FILE_BACKUP.exists():
        config_file_contents_backup = CONFIG_FILE_BACKUP.read_text()
    else:
        config_file_contents_backup = ''

    # If we have updated config
    if config_file_contents_new != config_file_contents_old:
        if config_file_contents_backup != config_file_contents_old and config_file_contents_backup != config_file_contents_new:
            # Backup current if backup does not match current OR new config
            CONFIG_FILE_BACKUP.write_text(config_file_contents_old)
        # Update the config file
        CONFIG_FILE.write_text(config_file_contents_new)

    if not REGISTRATION_FILE.exists():
        # Appservice registration file has not been created, this is probably the first run.
        # So let's generate it and copy it somewhere Synapse can find it.
        subprocess.check_call(['/docker-run.sh'])
        assert REGISTRATION_FILE.exists()
        if not REGISTRATIONS_DIR.is_dir():
            REGISTRATIONS_DIR.mkdir()

        # FIXME: Should I be regularly updating this?
        (REGISTRATIONS_DIR / 'mautrix-meta.yaml').write_text(REGISTRATION_FILE.read_text())
        print("Appservice registration yaml generated, go sort out registration before restarting this addon.",
              file=sys.stderr, flush=True)
    else:
        # Start normally
        print("Starting service", flush=True)
        subprocess.check_call(['/docker-run.sh'])
