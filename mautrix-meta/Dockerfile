FROM dock.mau.dev/mautrix/meta:v26.11

# I could probably drop this dependency, but then I'd be relying on the application to check the yaml for me.
RUN apk add py3-yaml

# Upstream's CMD is `CMD ["/docker-run.sh"]`, but it makes some assumptions about using /data.
# so I have an alternative entrypoint which replaces it
COPY start-optionsjson.py /
ENTRYPOINT ["/start-optionsjson.py"]
