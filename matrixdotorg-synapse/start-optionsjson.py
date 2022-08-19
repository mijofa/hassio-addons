#!/usr/local/bin/python
# FIXME: /usr/local? Really?
"""Small wrapper for start.py to read from Home Assistant's /data/options.json instead of environment variables."""
import json
import pathlib
import sys

import start  # Upstream's /start.py

OPTIONS_FILE = pathlib.Path('/data/options.json')
CONFIG_FILE = pathlib.Path('/data/homeserver.yaml')

if not OPTIONS_FILE.exists():
    raise Exception("No /data/options.json file")

# FIXME: Does the 'generate' path edit the environment at all?
#        If so, this dict will be in an unpredictable state going back into the next main call
env_opts = json.loads(OPTIONS_FILE.read_text())

# Turn all non-str options into strings.
# Dropping that are false bools as we actually don't want those set at all.
for key in list(env_opts.keys()):
    if env_opts[key] is False:
        env_opts.pop(key)
    elif env_opts[key] is True:
        env_opts[key] = "true"
    elif type(env_opts[key]) != str:
        env_opts[key] = str(env_opts[key])

if __name__ == "__main__":
    if not CONFIG_FILE.exists() and not (len(sys.argv) > 1 and sys.argv[1] == "generate"):
        print("Config file doesn't exist, generating")
        start.main([sys.argv[0], 'generate'], env_opts)
    print(sys.argv, env_opts)
    start.main(sys.argv, env_opts)
