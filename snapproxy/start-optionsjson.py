#!/usr/bin/python3
"""Small wrapper for the base upstream startup script to read config from Home Assistant's /data/options.json."""
import datetime
import grp
import json
import os
import pathlib
import pwd
import secrets
import stat
import subprocess
import sys

OPTIONS_FILE = pathlib.Path('/data/options.json')
CONFIG_FILE = pathlib.Path('/etc/snapserver.conf')
SECRET_FILE = pathlib.Path('/data/secret')
PULSE_COOKIE_FILE = pathlib.Path('/root/.config/pulse/cookie')

if not OPTIONS_FILE.exists():
    raise Exception("No /data/options.json file")

HA_options = json.loads(OPTIONS_FILE.read_text())
# FIXME: I can't use configparser because it doesn't allow for the duplicate source options I need to support
# NOTE: The chr(10) here is a '\n', but since we can't do '\' in f-string expressions it's the best way I could get around that.
config_template = f"""
[server]
threads = {HA_options['server_threads']}
datadir = {HA_options['server_datadir']}

[stream]
{chr(10).join('source = ' + source for source in HA_options['stream_sources'])}
sampleformat = {HA_options['stream_sampleformat']}
codec = {HA_options['stream_codec']}
chunk_ms = {HA_options['stream_chunk_ms']}
buffer = {HA_options['stream_buffer']}
send_to_muted = {HA_options['stream_send_to_muted']}

[http]
enabled = {HA_options['http_enabled']}
doc_root = /usr/share/snapserver/snapweb/

[tcp]
enabled = {HA_options['tcp_enabled']}

[logging]
sink = stderr
filter = {HA_options['logging_filter']}
"""

if __name__ == "__main__":
    print("Dumping config to config file", flush=True)
    CONFIG_FILE.write_text(config_template)

    if not SECRET_FILE.exists():
        print("generating secret", flush=True)
        SECRET_FILE.write_text(secrets.token_urlsafe())

    # Set up PulseAudio sink
    if not [line for line in subprocess.check_output(['pactl', 'list', 'sinks'], text=True).splitlines()
            if 'mijofa.snapcast-proxy = ' in line]:
        subprocess.check_call(['pactl', 'load-module', 'module-pipe-sink',
                               'file=/data/external/snapfifo',  # This ends up at /run/audio/snapfifo in the addon
                               'sink_name=snapfifo', 'format=s16le', 'rate=48000',
                               # FIXME: PulseAudio is messy in it's interpretation of the sink_properties argument
                               #        Don't touch this unless you're willing to figure it out.
                               *("""sink_properties="device.description='Snapcast\\ FIFO'"""
                                 """device.icon_name='mdi:cast-audio'"""
                                 f"""mijofa.snapcast-proxy='{datetime.datetime.now()}'""")])
        # FIXME: curl --silent --data '{}' -H "Authorization: Bearer $SUPERVISOR_TOKEN" http://supervisor/audio/reload

    # FIXME: Do Home Assistant discovery stuff for VLC
    # FIXME: Can I do discovery for MPD or Snapcast?

    # FIXME: This is mental, do something better
    # Before dropping privileges, fix permissions on pulse cookie so that nobody user can get to it.
    PULSE_COOKIE_FILE.chmod(PULSE_COOKIE_FILE.stat().st_mode | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)
    # And make each parent directory executable
    for p in PULSE_COOKIE_FILE.parents:
        p.chmod(p.stat().st_mode | stat.S_IXGRP | stat.S_IXOTH)

    # VLC won't run as root, so let's drop privileges
    # FIXME: Should we do this sooner?
    os.setgid(grp.getgrnam('audio').gr_gid)  # It's important this happens before os.setuid
    os.setuid(pwd.getpwnam('nobody').pw_uid)

    snapserver_args = ['snapserver', '-c', '/etc/snapserver.conf']
    vlc_args = ['cvlc', '--extraintf', 'telnet', '--telnet-password', SECRET_FILE.read_text().strip(),
                # Since the general purpose of this is for endless HTTP streams, set some options for those
                '--http-continuous', '--http-reconnect']

    processes = {}
    # FIXME: I should be setting environment variables for everything such that the fifo sink is the default
    snapserver = subprocess.Popen(snapserver_args)
    processes[snapserver.pid] = snapserver
    # FIXME: For some reason I can't understand this won't process all the arguments properly without shell=True
    #        Specifically if fails to do any of the telnet things properly.
    vlc = subprocess.Popen(vlc_args)
    processes[vlc.pid] = vlc

    # FIXME: Include mpd, as it seems to be the only controlable media player that doesn't struggle immensly at the beginning of a stream.
    #        On that note, get rid of VLC and just run 2 instances of mpd?
    #        Worth considering mopidy? I want this as minimal as possible, so probably not, but I don't think mpd is particularly active nowadays since mopidy is winning.

    crashed = False
    while crashed is False:
        pid, status = os.wait()
        print(pid, status, file=sys.stderr, flush=True)
        if pid in processes:
            crashed = processes.pop(pid)
            print(f"{crashed.args[0]} crashed, killing others and exiting.", file=sys.stderr, flush=True)
            for p in processes:
                print(f"Killing {p.args[0]}", file=sys.stderr, flush=True)
                p.kill()
