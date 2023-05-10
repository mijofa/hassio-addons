FROM kouinkouin/snappymail:2.27.3

RUN apt update && \
    apt install -y --no-install-recommends wireguard-tools iproute2 python3-yaml python3-pip && \
    python3 -m pip install heisenbridge
#RUN apk add wireguard-tools iproute2 py3-yaml py3-pip

# SnappyMail has a bunch of absolute URLs, but it tries to be clever about them and generates them based on the path in the request URI.
# (This seems to be a PHPism, since it was the same in RoundCube)
# Home Assistant's Ingress is trying to be clever by hiding the real request URI from the called web app.
# These 2 things conflict and break everything.
# Ingress does helplfully include an X-Ingress-Path header though, so let's trick the PHP parts into adding that to the request URI.
RUN echo 'auto_prepend_file=/usr/local/etc/php/ingress-fix-prepend.php' >/usr/local/etc/php/conf.d/ingress-fix.ini && \
    printf '%s\n' >/usr/local/etc/php/ingress-fix-prepend.php \
        '<?php if (isset($_SERVER["REQUEST_URI"]) AND isset($_SERVER["HTTP_X_INGRESS_PATH"])) {' \
        '    $_SERVER["REQUEST_URI"] = $_SERVER["HTTP_X_INGRESS_PATH"] . $_SERVER["REQUEST_URI"];' \
        '}'

# Built in entrypoint doesn't really support Home Assistant's config system,
# or running Heisenbridge as well.
# This wrapper script handles reading /data/options.json and running the entrypoint accordingly
COPY start-optionsjson.py /
ENTRYPOINT ["/start-optionsjson.py"]
CMD []
