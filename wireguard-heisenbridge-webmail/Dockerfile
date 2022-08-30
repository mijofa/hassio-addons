# FIXME: There is an Alpine build available, consider switching to that.
#        I confirmed it works alright, but was missing default Mutt config for colours and such.
#        I could copy them in, but it's 2am and I CBFed.
FROM tsl0922/ttyd:latest

RUN apt update && \
    apt install -y --no-install-recommends wireguard-tools iproute2 python3-yaml python3-pip vim && \
    python3 -m pip install heisenbridge && \
    DEBIAN_FRONTEND=noninteractive apt install -y --no-install-recommends neomutt && \
    usermod --home /data nobody  # I want to run mutt as 'nobody', but it needs a $HOME for mutt to store state and such

# ttyd's ENTRYPOINT is ['/usr/bin/tini', '--'] with a CMD of ['ttyd', 'bash']
# I don't care about tini, and I'm running ttyd myself in the start-optionsjson.py
COPY start-optionsjson.py /
ENTRYPOINT ["/start-optionsjson.py"]
