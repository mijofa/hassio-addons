FROM tsl0922/ttyd:alpine

# py3-ruamel.yaml is a dependency of heisenbridge, but fails to install in Pip for some reason.
# First glance looks like it's because 'gcc' is not available,
# but rather than digging through investigating and fixing that I just installed the distro packaged version instead.
RUN apk add wireguard-tools iproute2 py3-yaml py3-pip   py3-ruamel.yaml && \
    python3 -m pip install heisenbridge


# Snappymail's CMD is ["/entrypoint.sh"]
COPY start-optionsjson.py /
ENTRYPOINT ["/start-optionsjson.py"]
CMD ["apache2-foreground"]
