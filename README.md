This is my Home Assistant's _Supervisor_ add-ons repository.

Based on pla10 ("which was based on Raph2i with some smaller changes"),
with the add-ons I don't intend to use removed.
All Addons compile on your machine at installation, let it work.


Personal dev notes
------------------
The version number in config.yaml is a little picky,
I tried doing "myversion:upstreamversion" like "0.0.1:v1.27.0",
and the hasio server wouldn't build them.

TODO
====
* Add an 'etckeeper' add-on, to keep a git repo of the config directory.
  My thinking is, on startup, it'll do a commit & push (no pull), then stop.
  Optionally, it'll use a config value as the commit message, then clear that config option.

  Then there can be a regular automation "cronjob" to just start the add-on every night,
  and the user/admin can manually add that config option and start the add-on themselves for explicit changes.

* Give up on webmail (unless work updates Dovecot/Postfix), it's not worked for me.
  Remove it from the Heisenbridge add-on, and leave it just doing wireguard & heisenbridge.

* **snapproxy**: Support back/skip/etc from snapcast clients.
  Use upstream's meta_mpd.py, but rework it to control a Home Assistant media_player instead.
  What Media Player instance it controls would have to be configured in the UI as I can't programmatically determine what is my own media player
  FIXME: Maybe actually setup a fake "MPD" listener, so I can use various mpd clients to control Home Assistant, then plug this into that?
