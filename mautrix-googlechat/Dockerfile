FROM dock.mau.dev/mautrix/googlechat:v0.5.1
# NOTE: v0.4.0 enabled "appservice ephemeral events by default for new installations"
#       looks like I already had that enabled myself though... weird

# I could probably drop this dependency, but then I'd be relying on the application to check the yaml for me.
RUN apk add py3-yaml

# Upstream's CMD is `CMD ["/opt/mautrix-googlechat/docker-run.sh"]`, but I want to inject Home Assistant's config in before that,
# so I have an alternative entrypoint which will call the CMD afterwards
COPY start-optionsjson.py /
ENTRYPOINT ["/start-optionsjson.py"]
