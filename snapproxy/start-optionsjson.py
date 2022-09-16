#!/usr/bin/python3
"""Small wrapper for the base upstream startup script to read config from Home Assistant's /data/options.json."""
import datetime
import json
import os
import pathlib
import secrets
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
                               ("""sink_properties="device.description='Snapcast\\ FIFO' """
                                """device.icon_name='mdi:cast-audio' """
                                f"""mijofa.snapcast-proxy='{datetime.datetime.now()}'" """)])
        subprocess.check_call(['pactl', 'load-module', 'module-role-ducking',
                               'ducking_roles=music', 'trigger_roles=event',
                               'global=false', 'volume=75%'])
        # FIXME: This sink won't be seen by Home Assistant without telling it to reload, but do we care?
        #        curl --silent --data '{}' -H "Authorization: Bearer $SUPERVISOR_TOKEN" http://supervisor/audio/reload

    # Realistically, only one of these is actually necessary, but it doesn't hurt.
    subprocess.check_call(['pactl', 'set-default-sink', 'snapfifo'])
    os.environ['PULSE_SINK'] = 'snapfifo'

    # FIXME: Can I do discovery for MPD or Snapcast?

    snapserver_args = ['snapserver', '-c', '/etc/snapserver.conf']

    processes = {}
    # FIXME: I should be setting environment variables for everything such that the fifo sink is the default
    snapserver = subprocess.Popen(snapserver_args)
    processes[snapserver.pid] = snapserver

    # FIXME: MPD seems to be the only controlable media player that doesn't struggle immensly at the beginning of a stream.
    #        Worth considering mopidy?

    mpd_music = subprocess.Popen(['mpd', '--no-daemon', '/dev/stdin'], env={'PULSE_SINK': 'snapfifo'},
                                 stdin=subprocess.PIPE, text=True)
    print('include "/etc/mpd.conf"',
          'audio_output {',
          '   name          "Pulseaudio snapfifo for Snapcast"',
          '   type          "pulse"',
          '   sink          "snapfifo"',
          # '   mixer_type    "software"',
          '   media_role    "music"',
          '}',
          'port "6600"',
          sep='\n', file=mpd_music.stdin, flush=True)
    mpd_music.stdin.close()
    processes[mpd_music.pid] = mpd_music

    # FIXME: This one should be louder I think
    mpd_other = subprocess.Popen(['mpd', '--no-daemon', '/dev/stdin'], env={'PULSE_SINK': 'snapfifo'},
                                 stdin=subprocess.PIPE, text=True)
    # FIXME: Same as above except for port number, so make this a variable or something
    print('include "/etc/mpd.conf"',
          'audio_output {',
          '   name          "Pulseaudio snapfifo for Snapcast"',
          '   type          "pulse"',
          '   sink          "snapfifo"',
          # '   mixer_type    "software"',
          '   media_role    "event"',
          '}',
          'port "6601"',
          sep='\n', file=mpd_other.stdin, flush=True)
    mpd_other.stdin.close()
    processes[mpd_music.pid] = mpd_other

    # FIXME: It'd be great if I could get Pulseaudio to do role-ducking instead of HA changing the volumes of each stream

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
