#!/usr/bin/python3
"""Small wrapper for the base upstream startup script to read config from Home Assistant's /data/options.json."""
import json
import os
import pathlib
# import secrets
import socket
import subprocess
import sys

import yaml

OPTIONS_FILE = pathlib.Path('/data/options.json')
WIREGUARD_CONF = pathlib.Path('/etc/wireguard/wg0.conf')
REGISTRATION_FILE = (pathlib.Path('/share/matrix_appservices/') / socket.gethostname()).with_suffix('.yaml')
ROUNDCUBE_CONFIG = pathlib.Path('/var/www/html/config/config.docker.inc.php')

# I've symlinked some Roundcube directories into /data, but now Roundcube expects them to exist first
# FIXME: Is it safe to just symlink them to /data directly?
CONFIG_DIR = pathlib.Path('/data/config')
DB_DIR = pathlib.Path('/data/db')


if not OPTIONS_FILE.exists():
    raise Exception("No /data/options.json file")

HA_options = json.loads(OPTIONS_FILE.read_text())

# FIXME: Don't listen on the VPN IP address.
heisenbridge_args = ['--config', str(REGISTRATION_FILE), '--listen-address', '0.0.0.0',
                     '--owner', HA_options['heisenbridge_owner_mxid'], HA_options['heisenbridge_synapse_url']]

# PHPIZE_DEPS=$'autoconf \t\tdpkg-dev \t\tfile \t\tg++ \t\tgcc \t\tlibc-dev \t\tmake \t\tpkg-config \t\tre2c'
# PHP_ASC_URL=https://www.php.net/distributions/php-8.1.17.tar.xz.asc
# PHP_CFLAGS='-fstack-protector-strong -fpic -fpie -O2 -D_LARGEFILE_SOURCE -D_FILE_OFFSET_BITS=64'
# PHP_CPPFLAGS='-fstack-protector-strong -fpic -fpie -O2 -D_LARGEFILE_SOURCE -D_FILE_OFFSET_BITS=64'
# PHP_INI_DIR=/usr/local/etc/php
# PHP_LDFLAGS='-Wl,-O1 -pie'
# PHP_SHA256=b5c48f95b8e1d8624dd05fc2eab7be13277f9a203ccba97bdca5a1a0fb4a1460
# PHP_URL=https://www.php.net/distributions/php-8.1.17.tar.xz
# PHP_VERSION=8.1.17

# NOTE: Don't use ints or booleans, only strings.
snappymail_env = {
    # FIXME: Will this actually work?
    # # Inherit from the actual environment, for various upstream defaults (specifically the PHP vars)
    # **os.environ,

    'LOG_TO_STDERR': 'true',  # No point configuring this, always do logging
    'SECURE_COOKIES': 'true',  # Does this cause problems with HA's ingress?

    # FIXME: Make these configurable?
    'UPLOAD_MAX_SIZE': '25M',
    'MEMORY_LIMIT': '128M',

    # Don't make these configurable, I'm only even setting them in the first place because the entrypoint.sh script needs them
    'UID': '991',
    'GID': '991',
}


if __name__ == "__main__":
    # Generate registration.yaml if it doesn't already exist
    if not REGISTRATION_FILE.exists():
        print("Overwriting registration yaml.", flush=True)
        subprocess.check_call(['heisenbridge', '--generate', *heisenbridge_args])
        registration_yaml = yaml.safe_load(REGISTRATION_FILE.read_text())
        registration_yaml['url'] = HA_options['heisenbridge_own_url']
        REGISTRATION_FILE.write_text(yaml.dump(registration_yaml))
        print("Appservice registration yaml generated, go sort out registration before restarting this addon.",
              file=sys.stderr, flush=True)
    else:
        print('Writing wg-quick config', flush=True)
        WIREGUARD_CONF.write_text(
            '\n'.join((
                "[Interface]",
                "Address = {wireguard_own_IP}",
                "PrivateKey = {wireguard_private_key}",
                "[Peer]",
                "Endpoint = {wireguard_endpoint}",
                "PublicKey = {wireguard_public_key}",
                "AllowedIPs = {joined_wireguard_allowed_IPs}",
            )).format(**HA_options, joined_wireguard_allowed_IPs=', '.join(HA_options['wireguard_allowed_IPs'])))

        if not DB_DIR.exists():
            DB_DIR.mkdir()
        if not CONFIG_DIR.exists():
            CONFIG_DIR.mkdir()

        print('Starting Wireguard interface.', flush=True)
        subprocess.check_call(['wg-quick', 'up', 'wg0'])
        print('Got IP addresses;', flush=True)
        subprocess.check_call(['ip', '-oneline', 'address'])

        processes = {}

        print('Starting Heisenbridge with command:', ['heisenbridge', *heisenbridge_args], flush=True)
        heisenbridge = subprocess.Popen(['heisenbridge', *heisenbridge_args])
        processes[heisenbridge.pid] = heisenbridge

        print('Starting SnappyMail with env:', snappymail_env, flush=True)
        snappymail = subprocess.Popen(['/entrypoint.sh'], env=snappymail_env)
        processes[snappymail.pid] = snappymail

        crashed = False
        while crashed is False:
            pid, status = os.wait()
            print(pid, status, file=sys.stderr, flush=True)
            if pid in processes:
                crashed = processes.pop(pid)
                print(f"{crashed.args[0]} crashed, killing others and exiting.", file=sys.stderr, flush=True)
                for pid in processes:
                    print(f"Killing {processes[pid].args[0]}", file=sys.stderr, flush=True)
                    processes[pid].kill()
