So this doesn't **really** have anything to do with Home Assistant, but it was easier than creating a brand new repo.

M5Stack AtomS3-Lite Snapclient
==============================

Note that all the hardware can be swapped out for equivalents, but you'll have to patch the firmware builds accordingly.

Shopping list
-------------
* `AtomS3 Lite ESP32S3 Dev Kit<https://shop.m5stack.com/products/atoms3-lite-esp32s3-dev-kit?variant=43743077957889>`_
* `Atomic Audio 3.5 Base<https://shop.m5stack.com/products/atomic-audio-3-5-base>`_
  Sold out at time of writing, `ATOMIC Speaker Base (NS4168)<https://shop.m5stack.com/products/atomic-speaker-base-ns4168>`_ is likely suitable, but uses a different DAC so will require firmware modification.

Code
----

Use ESPHome Device Builder with m5stack-atoms3-lite-snapclient.yaml.
I did so with the dev build on 2026-06-18, but it should work with the stable version at that time and newer.
For posterity, it is version 2026.7.0-dev20260618 in Home Assistant.

This is a hamfisted amalgamation of:
* https://devices.esphome.io/devices/m5stack-atoms3-lite/
* https://docs.m5stack.com/en/homeassistant/media_player/atomic_audio_3.5_base
* https://github.com/m5stack/esphome-yaml/tree/main/components/es8311  which really should've been mentioned in the atomic_audio_3.5_base page above
* https://github.com/esphome/esphome/pull/14389

Notes
-----
We've noticed an annoying "pop" if unmuting after it's been muted for a while.
Sounds like capacitor discharge or similar, possibly ground leakage.
There was similar (and much worse) crackling/popping sounds when I was powering it from the TV's USB socket instead of a separate power brick.
I've swapped out some power bricks to something higher quality, going to see if that helps.

This device is fairly low on RAM and something online warned pretty heavily against having snapserver's buffer size above 500.
I have ignored that warning and set it to 1,000 and things have continued working.
Not yet sure if that was a good idea
