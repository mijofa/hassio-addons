ARG BUILD_FROM
FROM $BUILD_FROM

RUN apt update && apt install -y --no-install-recommends wireguard-tools iproute2 python3-yaml python3-pip && apt clean && python3 -m pip install heisenbridge

# Roundcube's ENTRYPOINT is `ENTRYPOINT ["/init"]`
COPY start-optionsjson.py /
ENTRYPOINT ["/start-optionsjson.py"]
CMD ["apache2-foreground"]
