#!/usr/local/bin/python
# FIXME: /usr/local? Really?
"""Small wrapper for start.py to read from Home Assistant's /data/options.json instead of environment variables."""
import json
import pathlib
import subprocess
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
            print('Skipping symlink', symlink_path, '->', symlink_dest, file=sys.stderr, flush=True)
    else:
        print('Symlinking', symlink_path, '->', symlink_dest, file=sys.stderr, flush=True)
        symlink_path.symlink_to(symlink_dest)

env_opts['SYNAPSE_NO_TLS'] = env_opts.get('SYNAPSE_NO_TLS', False)

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
        env_opts[key] = "false"
    elif env_opts[key] is True:
        env_opts[key] = "true"
    elif type(env_opts[key]) != str:
        env_opts[key] = str(env_opts[key])

print("CONFIG:", env_opts, file=sys.stderr, flush=True)
env_opts['SYNAPSE_NO_TLS'] = 'false'

if __name__ == "__main__":
    print("Generating config file regardless of existing state", file=sys.stderr, flush=True)
    subprocess.check_call([sys.executable, '/start.py', 'generate'], env=env_opts)
    print(sys.argv, env_opts, file=sys.stderr, flush=True)
    start.main(sys.argv, env_opts)
