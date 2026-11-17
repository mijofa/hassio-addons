#!/usr/bin/python3
"""Small wrapper for the base upstream startup script to read config from Home Assistant's /data/options.json."""
import json
import os
import pathlib
# import secrets
import subprocess
# import sys
# import time

# import yaml

if pathlib.Path('/data/config.yaml').exists():
    if not pathlib.Path('/config/config.yaml').exists():
        pathlib.Path('/config/config.yaml').write_bytes(pathlib.Path('/data/config.yaml').read_bytes())
        print("Copied config to new location, go check on that before continuing")
        print("/mnt/data/supervisor/apps/data/674b3982_mautrix-meta/ -> /mnt/data/supervisor/app_configs/674b3982_mautrix-meta/")
    else:
        print("Old config still exists, wtf?")

    exit()

CONFIG_FILE = pathlib.Path('/config/config.yaml')
REGISTRATION_FILE = pathlib.Path('/share/matrix_appservices/674b3982_mautrix-meta.yaml')
APPSERVICE_EXECUTABLE = pathlib.Path('/usr/bin/mautrix-meta')

if __name__ == "__main__":
    if not CONFIG_FILE.exists():
        subprocess.check_call([APPSERVICE_EXECUTABLE, '--config', CONFIG_FILE, '--generate-example-config'])
        os.chown(CONFIG_FILE, UID, GID)
        print("Didn't find a config file.")
        print("Copied default config file to", CONFIG_FILE)
        print("Modify that config file to your liking.")
        print("Start the container again after that to generate the registration file.")

        # FIXME: I'd really like to apply some more sensible defaults for the HA environments, but I can't do that while preserving comments/etc.
        #        So for now we ignore this.

        exit()
    elif not REGISTRATION_FILE.exists():
        subprocess.check_call([APPSERVICE_EXECUTABLE, '--generate-registration', '--config', CONFIG_FILE, '--registration', REGISTRATION_FILE])
        os.chown(REGISTRATION_FILE, UID, GID)
        print("Didn't find a registration file.")
        print("Generated one for you at", REGISTRATION_FILE)
        print("See https://docs.mau.fi/bridges/general/registering-appservices.html on how to use it.")

        exit()
    else:
        print("Starting service", flush=True)
        UID = int(os.environ['UID'])
        GID = int(os.environ.get('GID', UID))

        os.chdir('/data')  # FIXME: What actually belongs here?
        # Equivalent to the `chown -R ...` in docker-run.sh
        # FIXME: That runs on only /data, do we need only /config?
        for dirpath, dirnames, filenames in [*pathlib.Path('/config').walk(follow_symlinks=False),
                                             *pathlib.Path('/data').walk(follow_symlinks=False)]:
            os.chown(dirpath, UID, GID)
            for filename in filenames:
                os.chown(dirpath / filename, UID, GID)

        # This should be equivalent to `su-exec` as called from docker-run.sh
        # ref: https://github.com/ncopa/su-exec/blob/master/su-exec.c
        os.setgroups([GID])
        # os.setresgid(GID, GID, GID)
        os.setgid(GID)
        # os.setresuid(UID, UID, UID)  # Must be last, because it drops privs required for the above
        os.setuid(UID)  # Must be last, because it drops privs required for the above
        os.execl(APPSERVICE_EXECUTABLE, 'mautrix-meta', '--config', CONFIG_FILE, '--registration', REGISTRATION_FILE)
