#!/usr/local/bin/python
# FIXME: /usr/local? Really?
"""Small wrapper for start.py to read from Home Assistant's /data/options.json instead of environment variables."""
import json
import os
import pathlib
import secrets
import subprocess
import sys

import yaml

import start  # Upstream's /start.py
# import synapse._scripts.register_new_matrix_user  # Upstream's /usr/local/bin/register_new_matrix_user

OPTIONS_FILE = pathlib.Path('/data/options.json')
CONFIG_FILE = pathlib.Path('/data/homeserver.yaml')

if not OPTIONS_FILE.exists():
    raise Exception("No /data/options.json file")

HA_options = json.loads(OPTIONS_FILE.read_text())

# internal_options = {}
# for k in ['internally', 'used', 'keys', 'which', 'synapse', 'should not', 'see']:
#     internal_options[k] = HA_options.pop(k)

# FIXME: This will generate a new secret every single time.
#        Perhaps we could leave it in a file next to homeserver.yaml for referencing next time.
for secret in ['registration_shared_secret', 'macaroon_secret_key']:
    if not HA_options.get(secret):
        HA_options[secret] = secrets.token_urlsafe()

# Reading this in as YAML to dump it back out is unnecessary, but does't hurt, and might YAML syntax make errors more obvious
synapse_conf = yaml.safe_load(HA_options['homeserver.yaml'].format(**HA_options))

# There's a few options that are usually passed as environment variables anyway,
# I don't think they're required given I'm writing the config file myself, but it shouldn't hurt.
env_opts = {'SYNAPSE_REPORT_STATS': "no",
            'SYNAPSE_SERVER_NAME': HA_options['server_name']}

if __name__ == "__main__":
    homeserver_yaml = pathlib.Path('/data/homeserver.yaml')
    media_store_path = pathlib.Path(HA_options['media_store_path'])
    if not homeserver_yaml.exists():
        print("Homeserver.yaml doesn't exist, pregenerating configs", flush=True)
        # I do this generate step not for homeserver.yaml, but because I know it does other things like log.config too.
        subprocess.check_call([sys.executable, '/start.py', 'generate'],
                              env=env_opts)
        # FIXME: I tried doing this in Python threads, but the timer never triggered.
        # user_registration = threading.Timer(30, subprocess.check_call,
        #                                     (["register_new_matrix_user", "--config", " /data/homeserver.yaml", "--admin"
        #                                       "--user", HA_options['default_user'], "--password", HA_options['default_userpass'],
        #                                       "http://localhost:8008"],))
        # user_registration.start()
        user_registration = subprocess.Popen(("sleep 30 ; register_new_matrix_user --config  /data/homeserver.yaml "
                                              f"--user {HA_options['default_user']} --password {HA_options['default_userpass']} "
                                              "--admin http://localhost:8008"), shell=True)
    if not media_store_path.is_dir:
        # FIXME: This doesn't work at all
        media_store_path.mkdir()
        # 901 is the magic uid/gid that synapse runs as by default.
        # It can be overridden, but I think it has to be done with env vars, not homeserver.yaml.
        os.chown(media_store_path, 991, 991)
    print("Overwriting homeserver.yaml with custom config", flush=True)
    homeserver_yaml.write_text(yaml.dump(synapse_conf))
    print("Starting Synapse", flush=True)
    try:
        start.main(sys.argv, env_opts)
    finally:
        # If the user_registration command is still running, kill it.
        # Just in case Synapse failed to start before the registration happened
        user_registration.poll()
        if user_registration.returncode is None:
            user_registration.kill()
