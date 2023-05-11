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

# SnappyMail's default nginx listener has some bad headers, and the cookie path is wrong.
# Instead of trying to hack around changing that listener's config (which then messes with nginx_proxy redirect)
# I can just add an extra listener that proxies back into that one.
RUN printf '%s\n' >/etc/nginx/ingress_proxy.conf \
        'server {' \
        '  listen 8099;' \
        "  # Make this work in an iFrame for HA's Ingress" \
        '  add_header "X-Frame-Options" "SAMEORIGIN";' \
        '  # add_header "Access-Control-Allow-Origin" "*";' \
        '  # add_header "Access-Control-Allow-Credentials" "true";' \
        '  location / {' \
        "      # Proxy to SnappyMail's default Nginx listener" \
        '      proxy_pass http://localhost:8888;' \
        "      # Add the Ingress path to the cookie paths so they don't get sent to other HA add-ons" \
        '      proxy_cookie_path / $http_X_INGRESS_PATH/;' \
        '      # proxy_set_header Cookie $cookie_ingress_session;' \
        '  }' \
        '}'
# Since the SnappyMail dockerfile overwrites nginx.conf, I have to add my own include line instead of relying on conf.d
RUN sed --in-place '$i\ \ include /etc/nginx/ingress_proxy.conf;' /etc/nginx/nginx.conf

# Manifest.json can't be read through Ingress because Ingress requires authentication credentials
RUN sed --in-place '/link rel="manifest"/s/>$/ crossorigin="use-credentials">/' /snappymail/snappymail/v/*/app/templates/Index.html

# Built in entrypoint doesn't really support Home Assistant's config system,
# or running Heisenbridge as well.
# This wrapper script handles reading /data/options.json and running the entrypoint accordingly
COPY start-optionsjson.py /
ENTRYPOINT ["/start-optionsjson.py"]
CMD []
