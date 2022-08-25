FROM roundcube/roundcubemail:latest

RUN apt update && apt install -y --no-install-recommends wireguard-tools iproute2 python3-yaml python3-pip && apt clean && python3 -m pip install heisenbridge

RUN rmdir /var/roundcube/config && ln -s /data/config /var/roundcube/config && ln -s /data/db /var/roundcube/db

# Roundcube's ENTRYPOINT is `ENTRYPOINT ["/docker-entrypoint.sh"]` with a CMD of `CMD ["apache2-foreground"]`
# Note I *also* want to run Heisenbridge.
# This wrapper script does that, and handles the /data/options.json file
COPY start-optionsjson.py /
ENTRYPOINT ["/start-optionsjson.py"]
CMD ["apache2-foreground"]
