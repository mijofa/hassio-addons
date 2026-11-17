#!/usr/local/bin/python
# FIXME: /usr/local? Really?
"""Small wrapper for start.py to read from Home Assistant's /data/options.json instead of environment variables."""
import json
import os
import pathlib
import secrets
import subprocess
import sys
import urllib.parse

import yaml

import start  # Upstream's /start.py
# import synapse._scripts.register_new_matrix_user  # Upstream's /usr/local/bin/register_new_matrix_user

if pathlib.Path('/data/homeserver.yaml').exists():
    if not pathlib.Path('/config/homeserver.yaml').exists():
        pathlib.Path('/config/homeserver.yaml').write_bytes(pathlib.Path('/data/homeserver.yaml').read_bytes())
        print("Copied config to new location, go check on that before continuing")
        print("/mnt/data/supervisor/apps/data/674b3982_matrixdotorg-synapse/ -> /mnt/data/supervisor/app_configs/674b3982_matrixdotorg-synapse")
    else:
        print("Old config still exists, wtf?")
    
    exit()

OPTIONS_FILE = pathlib.Path('/data/options.json')
APPSERVICE_REGISTRATIONS_DIR = pathlib.Path('/share/matrix_appservices/')  # FIXME: Should this be configurable?
HOMESERVER_YAML = pathlib.Path('/config/homeserver.yaml')
ELEMENT_CONFIG_JSON, = pathlib.Path('/usr/local/lib/').glob('python3*/site-packages/synapse/static/config.json')


def parse_dburl(url: str):
    """Parse URL string into a database dict more useful to homeserver.yaml."""
    parsed_url = urllib.parse.urlparse(url)
    if parsed_url.scheme == 'sqlite':
        if parsed_url.path != '/data/homeserver.db':
            raise NotImplementedError("Can't set SQLite path via env vars... sorry")
        return {}
    elif parsed_url.scheme == 'postgres':
        assert parsed_url.password is not None
        assert parsed_url.password != ''

        queries = urllib.parse.parse_qs(parsed_url.query)
        return {'POSTGRES_USER': parsed_url.username or 'synapse',
                'POSTGRES_PASSWORD': parsed_url.password,
                'POSTGRES_DB': parsed_url.path.strip('/'),
                'POSTGRES_HOST': parsed_url.hostname,
                # NOTE: str -> int -> str is useful for input validation
                'POSTGRES_PORT': str(int(parsed_url.port or 0) or 5432),
                'POSTGRES_CP_MIN': str(int(*queries['cp_min']) or 5),
                'POSTGRES_CP_MAX': str(int(*queries['cp_max']) or 10)}
    else:
        raise NotImplementedError("Only support sqlite or postgres databases")


if not OPTIONS_FILE.exists():
    raise Exception("No /data/options.json file")

HA_options = json.loads(OPTIONS_FILE.read_text())

## Possible environment variables  # FIXME: Where did this come from?
# Mandatory config options:
# * SYNAPSE_SERVER_NAME
# * SYNAPSE_REPORT_STATS
# Known optional config options:
# * SYNAPSE_WORKER
# * SYNAPSE_CONFIG_DIR  # Should stay with default /data
# * SYNAPSE_CONFIG_PATH  # Should stay with default $SYNAPSE_CONFIG_DIR/homeserver.yaml
# * SYNAPSE_DATA_DIR  # Should stay with default /data
# * SYNAPSE_REGISTRATION_SHARED_SECRET  # DO NOT set this
# * SYNAPSE_ENABLE_REGISTRATION  # DO set this
# * SYNAPSE_MACAROON_SECRET_KEY  # DO NOT set this
# * SYNAPSE_HTTP_PORT  # default 8008
# * SYNAPSE_EVENT_CACHE_SIZE  # default '10K'
# * SYNAPSE_MAX_UPLOAD_SIZE  # default '50M'
# * SYNAPSE_ALLOW_GUEST  # default False
# * SYNAPSE_LOG_LEVEL  # Beware of setting this to DEBUG as that will put sensitive info in the logs
# * LOG_FILE_PATH  # Don't bother messing with this, the logs go out on the console anyway
# * SYNAPSE_LOG_SENSITIVE  # DO NOT set this, it lets sensitive info get into the logs
# * SYNAPSE_NO_TLS
# Recaptcha
# * SYNAPSE_RECAPTCHA_PUBLIC_KEY
# * SYNAPSE_RECAPTCHA_PRIVATE_KEY
# TURN
# * SYNAPSE_TURN_URIS
# * SYNAPSE_TURN_SECRET
# # Only for Postgres support
# * POSTGRES_PASSWORD
# * POSTGRES_USER  # default 'synapse'
# * POSTGRES_DB  # default 'synapse'
# * POSTGRES_HOST  # default 'db'
# * POSTGRES_PORT  # default '5432'
env_opts = {'SYNAPSE_REPORT_STATS': 'yes' if HA_options['report_stats'] else '',
            'SYNAPSE_SERVER_NAME': HA_options['server_name'],

            'SYNAPSE_CONFIG_DIR': '/config',  # FIXME: Is /data/ still more suitable for this?
            'SYNAPSE_CONFIG_PATH': str(HOMESERVER_YAML),

            'SYNAPSE_HTTP_PORT': str(8008),  # If this needs to be changed, do it in HA
            # 'SYNAPSE_NO_TLS':   # Let nginx handle this
            # 'SYNAPSE_ENABLE_METRICS':   # FIXME: This requires extra ports, can we make foo use of it for monit or similar? Perhaps some HA sensors?

            # 'SYNAPSE_RECAPTCHA_PUBLIC_KEY':   # FIXME: Useful?
            # 'SYNAPSE_RECAPTCHA_PRIVATE_KEY':   # FIXME: Useful?

            # 'SYNAPSE_TURN_URIS':   # FIXME: Useful?
            # 'SYNAPSE_TURN_SECRET':   # FIXME: Useful?

            # FIXME: Is this meant to be space separated?
            'SYNAPSE_APPSERVICES': ' '.join(str(appservice) for appservice in APPSERVICE_REGISTRATIONS_DIR.glob('*yaml')),

            **parse_dburl(HA_options['database_url']),
            }
if HA_options.get('enable_registration'):
    env_opts['SYNAPSE_ENABLE_REGISTRATION'] = 'yes'
if HA_options.get('registration_shared_secret'):
    env_opts['SYNAPSE_REGISTRATION_SHARED_SECRET'] = HA_options['registration_shared_secret']
if HA_options.get('macaroon_secret_key'):
    env_opts['SYNAPSE_MACAROON_SECRET_KEY'] = HA_options['macaroon_secret_key']
if HA_options.get('allow_guest_access'):
    env_opts['SYNAPSE_ALLOW_GUEST'] = 'yes'


if __name__ == "__main__":
    # media_store_path = pathlib.Path(HA_options['media_store_path'])
    user_registration = None
    if not HOMESERVER_YAML.exists():  # FIXME: This code path never gets tested
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
    # if not media_store_path.is_dir:
    #     # FIXME: This doesn't work at all
    #     media_store_path.mkdir()
    #     # 991 is the magic uid/gid that synapse runs as by default.
    #     # It can be overridden with $UID & $GID, but this is what I've tested
    #     os.chown(media_store_path, 991, 991)

    # Set default config for local instance of element-web
    element_options = json.load(ELEMENT_CONFIG_JSON.open('r'))
    element_options['default_server_name'] = HA_options['server_name']
    json.dump(element_options, ELEMENT_CONFIG_JSON.open('w'))

    print("Starting Synapse", flush=True)
    try:
        start.main(sys.argv, env_opts)
    finally:
        # If the user_registration command is still running, kill it.
        # Just in case Synapse failed to start before the registration happened
        if user_registration is not None:
            user_registration.poll()
            if user_registration.returncode is None:
                user_registration.kill()
