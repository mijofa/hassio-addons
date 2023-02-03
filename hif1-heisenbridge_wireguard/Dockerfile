# FIXME: There is an Alpine build available, consider switching to that.
#        I confirmed it works alright, but was missing default Mutt config for colours and such.
#        I could copy them in, but it's 2am and I CBFed.
FROM hif1/heisenbridge:1.14.1

# RUN apt update && \
#     apt install -y --no-install-recommends wireguard-tools iproute2 python3-yaml
RUN apk add wireguard-tools iproute2 py3-yaml py3-pip

# heisenbridge's ENTRYPOINT is ["heisenbridge", "-l", "0.0.0.0"] with a CMD of []
# But I *also* want to run Heisenbridge.
# This wrapper script does that, and handles the /data/options.json file
COPY start-optionsjson.py /
ENTRYPOINT ["/start-optionsjson.py"]
CMD []
