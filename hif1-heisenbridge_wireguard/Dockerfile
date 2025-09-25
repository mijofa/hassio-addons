# FIXME: This isn't maintained anymore, switch to https://hub.docker.com/r/djmaze/snappymail/tags
FROM hif1/heisenbridge:1.15.3

RUN apk add wireguard-tools iproute2 py3-yaml py3-pip

COPY 254_maxaudron:feature_user-presence.patch /opt/heisenbridge/
RUN apk add patch && \
    patch --directory=/opt/heisenbridge --strip=1 --input=254_maxaudron\:feature_user-presence.patch

# Built in entrypoint doesn't really support Home Assistant's config system,
# This wrapper script handles reading /data/options.json and running the entrypoint accordingly
COPY start-optionsjson.py /
ENTRYPOINT ["/start-optionsjson.py"]
CMD []
