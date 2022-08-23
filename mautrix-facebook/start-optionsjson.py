#!/usr/bin/python3
"""Small wrapper for the base upstream startup script to read config from Home Assistant's /data/options.json."""
import json
# import os
import pathlib
# import secrets
import subprocess

import yaml

OPTIONS_FILE = pathlib.Path('/data/options.json')
CONFIG_FILE = pathlib.Path('/data/config.yaml')

if not OPTIONS_FILE.exists():
    raise Exception("No /data/options.json file")

HA_options = json.loads(OPTIONS_FILE.read_text())

# internal_options = {}
# for k in ['internally', 'used', 'keys', 'which', 'synapse', 'should not', 'see']:
#     internal_options[k] = HA_options.pop(k)

# # FIXME: This will generate a new secret every single time.
# #        Perhaps we could leave it in a file next to homeserver.yaml for referencing next time.
# for secret in ['as_token:', 'hs_token:']:
#     if not HA_options.get(secret):
#         HA_options[secret] = secrets.token_urlsafe()

# Reading this in as YAML to dump it back out is unnecessary, but does't hurt, and might make YAML syntax errors more obvious
application_conf = yaml.safe_load(HA_options['config.yaml'].format(**HA_options))

if __name__ == "__main__":
    print("Overwriting config.yaml with custom config", flush=True)
    CONFIG_FILE.write_text(yaml.dump(application_conf))
    subprocess.check_call(['/opt/mautrix-facebook/docker-run.sh'])
