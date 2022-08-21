FROM matrixdotorg/synapse:v1.65.0

# Upstream's entrypoint is `["/start.py"]` but I want to inject Home Assistant's config in before that,
# so I have an alternative entrypoint which will call start.py itself

# This is already installed as it's also a dependency of Synapse... Mentioning it here though so that future me remembers it's required by my startup script.
#RUN apt install -y python3-yaml
COPY start-optionsjson.py /

ENTRYPOINT ["/start-optionsjson.py"]
