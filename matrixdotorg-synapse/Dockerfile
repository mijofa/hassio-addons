FROM matrixdotorg/synapse:latest
# FIXME: I should probably target the specific current version rather than always "latest"

COPY start-optionsjson.py /

# NOTE: Upstream's entrypoint is `["/start.py"]` so if I want to somehow inject Home Assistant's config in,
#       I'd have a 'run.sh' or similar which will read Home Assistant's config, then call out to start.py at the end.
# For testing purposes, I don't want it to actually run the start.sh yet
ENTRYPOINT ["/start-optionsjson.py"]
