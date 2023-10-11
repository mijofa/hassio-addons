FROM dock.mau.dev/mautrix/facebook:v0.5.1
# FIXME: v0.4.1 added a "MAUTRIX_DIRECT_STARTUP" option, I should probably use it here
#        https://github.com/mautrix/facebook/commit/4301673bed7cecd0b1dfda142d2b4a707509f826

# I could probably drop this dependency, but then I'd be relying on the application to check the yaml for me.
RUN apk add py3-yaml

# Upstream's CMD is `CMD ["/opt/mautrix-facebook/docker-run.sh"]`, but I want to inject Home Assistant's config in before that,
# so I have an alternative entrypoint which will call the CMD afterwards
COPY start-optionsjson.py /
ENTRYPOINT ["/start-optionsjson.py"]
