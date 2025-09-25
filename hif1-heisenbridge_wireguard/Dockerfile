# FIXME: This isn't maintained anymore, switch to https://hub.docker.com/r/djmaze/snappymail/tags
FROM hif1/heisenbridge:1.15.3

RUN apk add wireguard-tools iproute2 py3-yaml py3-pip

# Built in entrypoint doesn't really support Home Assistant's config system,
# This wrapper script handles reading /data/options.json and running the entrypoint accordingly
COPY start-optionsjson.py /
ENTRYPOINT ["/start-optionsjson.py"]
CMD []
