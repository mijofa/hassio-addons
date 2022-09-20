FROM sailfrog/cypht-docker:latest

RUN apk add python3
RUN ln -s /data/hm3 /var/lib/hm3

# FIXME: I believe this is an upstream bug, file it.
#        Wait, no, those options aren't properly in the hm3.ini file anyway... what's going on with these?
#        Hrmmm, they're in hm3.sample.ini in the upstream repo, so maybe they do exist? Unsure, let's just try it and see
RUN sed -i 's/config.ini/${CYPHT_CONFIG_FILE}/' docker-entrypoint.sh

# Cypht's ENTRYPOINT is `ENTRYPOINT ["docker-entrypoint.sh"]` with a CMD of `CMD ["php-fpm"]`
# This wrapper script does that, and handles the /data/options.json file
COPY start-optionsjson.py /
ENTRYPOINT ["/start-optionsjson.py"]
CMD ["php-fpm"]
