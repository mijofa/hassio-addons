#!/usr/local/bin/python
# FIXME: /usr/local? Really?
"""Small wrapper for start.py to read from Home Assistant's /data/options.json instead of environment variables."""
import json
import pathlib
import sys

import start  # Upstream's /start.py

if __name__ == "__main__":
    start.main(sys.argv, json.loads(pathlib.Path('/data/options.json').read_text()))
