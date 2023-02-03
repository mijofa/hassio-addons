FROM matrixdotorg/synapse:v1.76.0
# FIXME: Doing a huge version number jump, there's bound to be issues... right?
#        1.65.0 -> 1.72.0

# Download the latest version of element-web to Synapse's static directory
RUN apt update && apt install -y jq && apt clean
RUN curl -sSL $(curl --silent https://api.github.com/repos/vector-im/element-web/releases/latest | \
                  jq --raw-output '.assets[] | select(.name|endswith(".tar.gz")) | .browser_download_url') | \
        tar --gunzip --extract --strip-components=1 --directory /usr/local/lib/python*/site-packages/synapse/static
# Force synapse to actually allow its static resources to be iframed by ingress
# FIXME: Is this still necessary?
RUN sed -i "/Content-Security-Policy/ s/frame-ancestors 'none';/frame-ancestors 'self';/" /usr/local/lib/python3.11/site-packages/synapse/http/server.py

RUN curl -sSL https://github.com/devture/matrix-synapse-shared-secret-auth/raw/2.0.2/shared_secret_authenticator.py --output /usr/local/lib/python3.11/site-packages/shared_secret_authenticator.py

# Upstream's entrypoint is `["/start.py"]` but I want to inject Home Assistant's config in before that,
# so I have an alternative entrypoint which will call start.py itself

# This is already installed as it's also a dependency of Synapse... Mentioning it here though so that future me remembers it's required by my startup script.
#RUN apt install -y python3-yaml
COPY start-optionsjson.py /

ENTRYPOINT ["/start-optionsjson.py"]
