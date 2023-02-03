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
