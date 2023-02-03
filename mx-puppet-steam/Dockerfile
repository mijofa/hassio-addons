# FIXME: This upstream image doesn't use version numbers, and has **only** a latest tag.
FROM icewind1991/mx-puppet-steam:latest

# I could probably drop this dependency, but then I'd be relying on the application to check the yaml for me.
# Why the fuck does py3-yaml not bring python3 in?
RUN apk add python3 py3-yaml

# Upstream's ENTRYPOINT is `ENTRYPOINT ["/opt/mx-puppet-steam/docker-run.sh"]`, but I want to inject Home Assistant's config in before that,
# so I have an alternative entrypoint which will call the upstream one afterwards
COPY start-optionsjson.py /
ENTRYPOINT ["/start-optionsjson.py"]
