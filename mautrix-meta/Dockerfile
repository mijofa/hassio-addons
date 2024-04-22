FROM dock.mau.dev/mautrix/meta:v0.3.0

# I could probably drop this dependency, but then I'd be relying on the application to check the yaml for me.
RUN apk add py3-yaml

# Upstream's CMD is `CMD ["/docker-run.sh"]`, but I want to inject Home Assistant's config in before that,
# so I have an alternative entrypoint which will call the CMD afterwards
COPY start-optionsjson.py /
ENTRYPOINT ["/start-optionsjson.py"]
