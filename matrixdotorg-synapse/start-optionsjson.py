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

# Create symlinks for SSL certs and such
symlink_paths = {
    'tls_certificate_path': '/data/{SYNAPSE_SERVER_NAME}.tls.crt'.format(**env_opts),
    'tls_private_key_path': '/data/{SYNAPSE_SERVER_NAME}.tls.key'.format(**env_opts),
    'signing_key_path': '/data/{SYNAPSE_SERVER_NAME}.signing.key'.format(**env_opts),
}
for key in symlink_paths.keys():
    symlink_path = pathlib.Path(symlink_paths[key])
    symlink_dest = pathlib.Path(env_opts.pop(key).format(**env_opts))
    if symlink_path.exists():
        if symlink_path.readlink().resolve() != symlink_dest.resolve():
            raise Exception(f"Symlink '{symlink_path}' already exists and doesn't match")
        else:
            print('Skipping symlink', symlink_path, '->', symlink_dest)
    else:
        print('Symlinking', symlink_path, '->', symlink_dest)
        symlink_path.symlink_to(symlink_dest)

# Turn all non-str options into strings.
# Dropping that are false bools as we actually don't want those set at all.
for key in list(env_opts.keys()):
    if key == 'SYNAPSE_REPORT_STATS':
        # This one's special because it's required but can be "no"
        if env_opts[key] is False:
            env_opts[key] = "no"
        else:
            env_opts[key] = "yes"
    elif env_opts[key] is False:
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
