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

::

    wifi:
      ssid: !secret wifi_ssid
      password: !secret wifi_password
      # # ref: https://github.com/esphome/esphome/pull/14389
      # post_connect_roaming: false  # No resyncs after 5, 10 and 15 minutes
    substitutions:
      # The internal name used by ESPHome (use lowercase, no spaces, hyphens OK)
      devicename: "m5s-atoms3lite-media-player"
      # The friendly name shown in Home-Assistant & Snapcast/Music-Assistant (can have spaces and capitals)
      friendly_name: "Lounge room"
      # Description of what this device does. I don't konw where this shows up.
      device_comment: "Snapcast media player for the lounge room"

      i2s_dout_pin: GPIO5
      i2s_lrclk_pin: GPIO6
      i2s_bclk_pin: GPIO8
      i2c_sda: GPIO38
      i2c_scl: GPIO39
    api:
      encryption:
        key: [redacted]
    ota:
      - platform: esphome
    esp32:
      board: esp32-s3-devkitc-1
      flash_size: 8MB
      variant: ESP32S3
    logger:
      baud_rate: 0
      level: VERBOSE
    esphome:
      name: ${devicename}
      friendly_name: ${friendly_name}
      comment: ${device_comment}
    packages:
      remote_package_files:
        url: https://github.com/mijofa/hassio-addons
        files: [ESPHome/m5stack-atomic-audio3.5base-snapclient.yaml]
        # FIXME: Rename this upstream, cool kids use 'main' now
        ref: master
        refresh: 0s


Notes
-----
We've noticed an annoying "pop" if unmuting after it's been muted for a while.
Sounds like capacitor discharge or similar, possibly ground leakage.
There was similar (and much worse) crackling/popping sounds when I was powering it from the TV's USB socket instead of a separate power brick.
I've swapped out some power bricks to something higher quality, going to see if that helps.

This device is fairly low on RAM and something online warned pretty heavily against having snapserver's buffer size above 500.
I have ignored that warning and set it to 1,000 and things have continued working.
Not yet sure if that was a good idea
