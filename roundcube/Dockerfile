FROM roundcube/roundcubemail:latest

RUN apt update && apt install -y --no-install-recommends python3 && apt clean

RUN rmdir /var/roundcube/config && ln -s /data/config /var/roundcube/config && ln -s /data/db /var/roundcube/db

# Roundcube has a bunch of absolute URLs, but it tries to be clever about them and generates them based on the path in the request URI.
# Home Assistant's Ingress is trying to be clever by hiding the real request URI from the called web app.
# These 2 things conflict and break everything.
# FIXME: This will likely get fixed upstream: https://github.com/roundcube/roundcubemail-docker/issues/186
# Ingress does helplfully include an X-Ingress-Path header though, so let's trick the PHP parts into adding that to the request URI.
RUN echo 'auto_prepend_file=/usr/local/etc/php/ingress-fix-prepend.php' >/usr/local/etc/php/conf.d/ingress-fix.ini && \
    printf '%s\n' >/usr/local/etc/php/ingress-fix-prepend.php \
        '<?php if (isset($_SERVER["REQUEST_URI"]) AND isset($_SERVER["HTTP_X_INGRESS_PATH"])) {' \
        '    $_SERVER["REQUEST_URI"] = $_SERVER["HTTP_X_INGRESS_PATH"] . $_SERVER["REQUEST_URI"];' \
        '}'

# Roundcube's ENTRYPOINT is `ENTRYPOINT ["/docker-entrypoint.sh"]` with a CMD of `CMD ["apache2-foreground"]`
# Note I *also* want to run Heisenbridge.
# This wrapper script does that, and handles the /data/options.json file
COPY start-optionsjson.py /
ENTRYPOINT ["/start-optionsjson.py"]
CMD ["apache2-foreground"]
