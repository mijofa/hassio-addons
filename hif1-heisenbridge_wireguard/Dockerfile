FROM kouinkouin/snappymail:2.27.3

RUN apt update && \
    apt install -y --no-install-recommends wireguard-tools iproute2 python3-yaml python3-pip && \
    apt install -y --no-install-recommends python3-bcrypt && \
    python3 -m pip install heisenbridge
#RUN apk add wireguard-tools iproute2 py3-yaml py3-pip

# SnappyMail has a bunch of absolute URLs, but it tries to be clever about them and generates them based on the path in the request URI.
# (This seems to be a PHPism, since it was the same in RoundCube)
# Home Assistant's Ingress is trying to be clever by hiding the real request URI from the called web app.
# These 2 things conflict and break everything.
# Ingress does helplfully include an X-Ingress-Path header though, so let's trick the fastcgi & PHP parts into understanding that.
RUN printf '%s\n' >>/etc/nginx/fastcgi_params \
        "# Add support for Home Assistant's Ingress feature" \
        'fastcgi_param  SCRIPT_NAME        $http_X_INGRESS_PATH/$fastcgi_script_name;'
# Seems X-Frame-Options is set to DENY by default, let's mess with that too
# FIXME: What about other HSTS/CSP/CORS/etc headers?
RUN sed --in-place "/\s*listen\s\+8888\s*;/a# Make this work in an iFrame for HA's Ingress\nadd_header X-Frame-Options \"SAMEORIGIN\";" /etc/nginx/nginx.conf

# Built in entrypoint doesn't really support Home Assistant's config system,
# or running Heisenbridge as well.
# This wrapper script handles reading /data/options.json and running the entrypoint accordingly
COPY start-optionsjson.py /
ENTRYPOINT ["/start-optionsjson.py"]
CMD []
