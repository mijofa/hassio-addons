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


if not OPTIONS_FILE.exists():
    raise Exception("No /data/options.json file")

HA_options = json.loads(OPTIONS_FILE.read_text())

# FIXME: Don't listen on the VPN IP address.
heisenbridge_args = ['--config', str(REGISTRATION_FILE), '--listen-address', '0.0.0.0',
                     '--owner', HA_options['heisenbridge']['owner_mxid'], HA_options['heisenbridge']['synapse_url']]

if __name__ == "__main__":
    # Generate registration.yaml if it doesn't already exist
    if not REGISTRATION_FILE.exists():
        print("Overwriting registration yaml.", flush=True)
        subprocess.check_call(['heisenbridge', '--generate', *heisenbridge_args])
        registration_yaml = yaml.safe_load(REGISTRATION_FILE.read_text())
        registration_yaml['url'] = HA_options['heisenbridge']['own_url']
        REGISTRATION_FILE.write_text(yaml.dump(registration_yaml))

    print('Starting Wireguard interface.', flush=True)
    WIREGUARD_CONF.write_text(
        '\n'.join((
            "[Interface]",
            "Address = {own_IP}",
            "PrivateKey = {private_key}",
            "[Peer]",
            "Endpoint = {endpoint}",
            "PublicKey = {public_key}",
            "AllowedIPs = {allowed_IPs}",
        )).format(**HA_options['wireguard']))
    subprocess.check_call(['wg-quick', 'up', 'wg0'])

    print('Got IP addresses;', flush=True)
    subprocess.check_call(['ip', '-oneline', 'address'])
    print('Starting Heisenbridge with command:', ['heisenbridge', *heisenbridge_args], flush=True)
    heisenbridge = subprocess.Popen(['heisenbridge', *heisenbridge_args])
    roundcube = subprocess.Popen(['sleep', 'infinity'])

    crashed = False
    while crashed is False:
        pid, status = os.wait()
        print(pid, status, file=sys.stderr, flush=True)
        if pid == heisenbridge.pid:
            crashed = True
            print("Heisenbridge exited, killing Roundcube and exiting.", file=sys.stderr, flush=True)
            roundcube.kill()
        elif pid == roundcube.pid:
            crashed = True
            print("Roundcube exited, killing Heisenbridge and exiting.", file=sys.stderr, flush=True)
            heisenbridge.kill()
