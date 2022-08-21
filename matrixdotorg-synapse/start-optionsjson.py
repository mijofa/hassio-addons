#!/usr/local/bin/python
# FIXME: /usr/local? Really?
"""Small wrapper for start.py to read from Home Assistant's /data/options.json instead of environment variables."""
import json
import pathlib
import subprocess
import sys

# import yaml

import start  # Upstream's /start.py

OPTIONS_FILE = pathlib.Path('/data/options.json')
CONFIG_FILE = pathlib.Path('/data/homeserver.yaml')

if not OPTIONS_FILE.exists():
    raise Exception("No /data/options.json file")

HA_options = json.loads(OPTIONS_FILE.read_text())

# internal_options = {}
# for k in ['internally', 'used', 'keys', 'which', 'synapse', 'should not', 'see']:
#     internal_options[k] = HA_options.pop(k)

print(HA_options, file=sys.stderr, flush=True)
# synapse_conf = yaml.dump(HA_options).format(**HA_options)
# print(synapse_conf, file=sys.stderr, flush=True)
synapse_conf = HA_options['homeserver.yaml'].format(**HA_options)

# There's a few options that are usually passed as environment variables anyway,
# I don't think they're required given I'm writing the config file myself, but it shouldn't hurt.
env_opts = {'SYNAPSE_REPORT_STATS': "no",
            'SYNAPSE_SERVER_NAME': HA_options['server_name']}

if __name__ == "__main__":
    homeserver_yaml = pathlib.Path('/data/homeserver.yaml')
    if not homeserver_yaml.exists():
        print("Homeserver.yaml doesn't exist, pregenerating configs", file=sys.stderr, flush=True)
        subprocess.check_call([sys.executable, '/start.py', 'generate'],
                              env=env_opts)
    print("Overwriting homeserver.yaml with custom config", file=sys.stderr, flush=True)
    homeserver_yaml.write_text(synapse_conf)
    print(sys.argv, file=sys.stderr, flush=True)
    start.main(sys.argv, env_opts)
