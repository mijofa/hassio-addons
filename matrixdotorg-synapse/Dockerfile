# FIXME: Should this eventually be "element-hq"?
FROM matrixdotorg/synapse:v1.165.0
# FIXME: Doing a huge version number jump, there's bound to be issues... right?
#        1.65.0 -> 1.72.0 -> 1.96.1 -> 1.98.0
#        1.138.2 -> 1.165.0

# Download the latest version of element-web to Synapse's static directory
RUN apt update && apt install -y jq && apt clean
RUN curl -sSL $(curl --silent https://api.github.com/repos/element-hq/element-web/releases/latest | \
                  jq --raw-output '.assets[] | select(.name|endswith(".tar.gz")) | .browser_download_url') | \
        tar --gunzip --extract --strip-components=1 --directory /usr/local/lib/python3*/site-packages/synapse/static
# Force synapse to actually allow its static resources to be iframed by ingress
# FIXME: This is probably a bad idea for securit reasons...
RUN sed -i "/Content-Security-Policy/ s/frame-ancestors 'none';/frame-ancestors 'self';/" /usr/local/lib/python3*/site-packages/synapse/http/server.py
# Update the Element Web config
# FIXME: Wrap this better
RUN cd /usr/local/lib/python*/site-packages/synapse/static/ && jq --sort-keys --monochrome-output \
      '. | .default_device_display_name = "Home Assistant Ingress" | .disable_3pid_login = true | .disable_guests = true | .disable_custom_urls = true | del(.default_server_config) | .default_server_name = "Replaced at startup by start-optionsjson.py" | .branding.login_for_welcome = true' \
      config.sample.json  >config.json

# I do not believe this is used or useful anymore
# RUN curl -sSL https://github.com/devture/matrix-synapse-shared-secret-auth/raw/2.0.3/shared_secret_authenticator.py --output /usr/local/lib/python3.12/site-packages/shared_secret_authenticator.py

# Upstream's entrypoint is `["/start.py"]` but I want to inject Home Assistant's config in before that,
# so I have an alternative entrypoint which will call start.py itself

# This is already installed as it's also a dependency of Synapse... Mentioning it here though so that future me remembers it's required by my startup script.
#RUN apt install -y python3-yaml
COPY start-optionsjson.py /

ENTRYPOINT ["/start-optionsjson.py"]
