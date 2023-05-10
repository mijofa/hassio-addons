FROM kouinkouin/snappymail:2.27.3

RUN apt update && \
    apt install -y --no-install-recommends wireguard-tools iproute2 python3-yaml python3-pip && \
    python3 -m pip install heisenbridge
#RUN apk add wireguard-tools iproute2 py3-yaml py3-pip

# Built in entrypoint doesn't really support Home Assistant's config system,
# or running Heisenbridge as well.
# This wrapper script handles reading /data/options.json and running the entrypoint accordingly
COPY start-optionsjson.py /
ENTRYPOINT ["/start-optionsjson.py"]
CMD []
