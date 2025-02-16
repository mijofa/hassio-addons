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

OPTIONS_FILE = pathlib.Path('/data/options.json')
CONFIG_FILE = pathlib.Path('/data/homeserver.yaml')
APPSERVICE_REGISTRATIONS_DIR = pathlib.Path('/share/matrix_appservices/')  # FIXME: Should this be configurable?
HOMESERVER_YAML = pathlib.Path('/data/homeserver.yaml')
HOMESERVER_YAML_fordiff = pathlib.Path('/data/homeserver.yaml.custom')
ELEMENT_CONFIG_JSON = pathlib.Path('/usr/local/lib/python3.12/site-packages/synapse/static/config.json')


def parse_dburl(url: str):
    """Parse URL string into a database dict more useful to homeserver.yaml."""
    parsed_url = urllib.parse.urlparse(url)
    if parsed_url.scheme == 'sqlite':
        return {'name': 'sqlite3',
                'args': {'database': parsed_url.path}}
    elif parsed_url.scheme == 'postgres':
        queries = urllib.parse.parse_qs(parsed_url.query)
        return {'name': 'psycopg2',
                'args': {'user': parsed_url.username,
                         'password': parsed_url.password,
                         'database': parsed_url.path.strip('/'),
                         'host': parsed_url.hostname,
                         'port': parsed_url.port or 5432,
                         # NOTE: The expansion here is turn a single-item list into a single string argument
                         'cp_min': int(*queries['cp_min']),
                         'cp_max': int(*queries['cp_max'])}}
    else:
        raise NotImplementedError("Only support sqlite or postgres databases")


if not OPTIONS_FILE.exists():
    raise Exception("No /data/options.json file")

HA_options = json.loads(OPTIONS_FILE.read_text())

# internal_options = {}
# for k in ['internally', 'used', 'keys', 'which', 'synapse', 'should not', 'see']:
#     internal_options[k] = HA_options.pop(k)

if HOMESERVER_YAML.exists():
    old_homeserver_conf = yaml.safe_load(HOMESERVER_YAML.read_text())
else:
    old_homeserver_conf = {}
for secret in ['registration_shared_secret', 'macaroon_secret_key']:
    HA_options[secret] = HA_options.get(secret,
                                        old_homeserver_conf.get(secret,
                                                                secrets.token_urlsafe()))

# Reading this in as YAML to dump it back out is unnecessary, but doesn't hurt, and might make YAML syntax errors more obvious
# Also it's ended up helping modify it on the fly for appservices and database URL.
synapse_conf = yaml.safe_load(HA_options['homeserver.yaml'].format(**HA_options))

if HA_options['autofill_appservices'] and APPSERVICE_REGISTRATIONS_DIR.exists():
    assert synapse_conf.get('app_service_config_files', "Autogenerated by startup scripts") == "Autogenerated by startup scripts"
    synapse_conf['app_service_config_files'] = [str(appservice) for appservice in APPSERVICE_REGISTRATIONS_DIR.glob('*yaml')]

if HA_options['database_url']:
    assert synapse_conf.get('database', "Autogenerated by startup scripts") == "Autogenerated by startup scripts"
    synapse_conf['database'] = parse_dburl(HA_options['database_url'])

if HA_options['shared_secret_auth']:
    if 'modules' not in synapse_conf:
        synapse_conf['modules'] = []

    synapse_conf['modules'].append({'module': 'shared_secret_authenticator.SharedSecretAuthProvider',
                                    'config': {'shared_secret': HA_options['shared_secret_auth'],
                                               'm_login_password_support_enabled': True}})

# There's a few options that are usually passed as environment variables anyway,
# I don't think they're required for general use given I'm writing the config file myself, but it doesn't hurt.
# It only crashes without these on the initial generation step when Synapse tries to generate a homeserver.yaml from this variables
env_opts = {'SYNAPSE_REPORT_STATS': "no",
            'SYNAPSE_SERVER_NAME': HA_options['server_name']}

if __name__ == "__main__":
    media_store_path = pathlib.Path(HA_options['media_store_path'])
    if not HOMESERVER_YAML.exists():
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

    # Set default config for local instance of element-web
    if ELEMENT_CONFIG_JSON.exists():
        element_options = json.load(ELEMENT_CONFIG_JSON.open('r'))
    else:
        element_options = json.load(ELEMENT_CONFIG_JSON.with_suffix('.sample' + ELEMENT_CONFIG_JSON.suffix).open('r'))

    element_options['default_server_config']['m.homeserver'].update({
        'base_url': HA_options['public_baseurl'],
        'server_name': HA_options['server_name'],
    })
    element_options.update({
        'default_device_display_name': "Home Assistant Ingress",  # Necessary to avoid "400 - Device display name is too long"
        'disable_3pid_login': True,
        'disable_guests': True,
        'disable_custom_urls': True,
    })
    json.dump(element_options, ELEMENT_CONFIG_JSON.open('w'))

    print("Overwriting homeserver.yaml with custom config", flush=True)
    HOMESERVER_YAML.write_text(yaml.dump(synapse_conf))
    # Also write out to a separate file so that we can shell in and compare when Synapse makes changes itself
    HOMESERVER_YAML_fordiff.write_text(yaml.dump(synapse_conf))
    print("Starting Synapse", flush=True)
    try:
        start.main(sys.argv, env_opts)
    finally:
        # If the user_registration command is still running, kill it.
        # Just in case Synapse failed to start before the registration happened
        user_registration.poll()
        if user_registration.returncode is None:
            user_registration.kill()
