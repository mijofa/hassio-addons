FROM kouinkouin/snappymail:2.29.1

RUN apt update && \
    apt install -y --no-install-recommends wireguard-tools iproute2 python3-yaml python3-pip && \
    apt install -y --no-install-recommends python3-bcrypt && \
    python3 -m pip install heisenbridge
RUN rm -rf /var/lib/apt/lists/*
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
RUN printf '%s\n' >/etc/nginx/ingress_redirect-security_headers.conf \
        '# The fcgi app is setting "X-Frame-Options: DENY", which breaks Ingress' \
        'fastcgi_hide_header "X-Frame-Options";' \
        "# SAMEORIGIN isn't good enough though, because we're redirecting to a separate cname" \
        '# add_header "X-Frame-Options" "SAMEORIGIN";' \
        'add_header "Content-Security-Policy" "frame-ancestors {{REPLACEME_FRAME_ANCESTOR}};" always;' \
        "# I don't have good reason for each of these, I just copied them from upstream: https://github.com/the-djmaze/snappymail/wiki/Installation-instructions#nginx" \
        'add_header Strict-Transport-Security "max-age=15768000; includeSubDomains; preload;" always;' \
        'add_header X-Content-Type-Options "nosniff" always;' \
        'add_header X-XSS-Protection "1; mode=block" always;' \
        'add_header X-Robots-Tag "none" always;' \
        'add_header X-Download-Options "noopen" always;' \
        'add_header X-Permitted-Cross-Domain-Policies "none" always;' \
        'add_header Referrer-Policy "no-referrer" always;'
# Since the SnappyMail dockerfile overwrites nginx.conf, I have to add my own include line instead of relying on conf.d
RUN sed --in-place '$i\ \ include /etc/nginx/ingress_redirect-security_headers.conf;' /etc/nginx/nginx.conf

# Not relevant because we're doing a redirect instead of proxy_pass.
# https://github.com/home-assistant/supervisor/issues/4290
# # Manifest.json can't be read through Ingress because Ingress requires authentication credentials
# RUN sed --in-place '/link rel="manifest"/s/>$/ crossorigin="use-credentials">/' /snappymail/snappymail/v/*/app/templates/Index.html

# Built in entrypoint doesn't really support Home Assistant's config system,
# or running Heisenbridge as well.
# This wrapper script handles reading /data/options.json and running the entrypoint accordingly
COPY start-optionsjson.py /
ENTRYPOINT ["/start-optionsjson.py"]
CMD []
