FROM sailfrog/cypht-docker:latest

RUN apk add python3
RUN ln -s /data/hm3 /var/lib/hm3

# Cypht's ENTRYPOINT is `ENTRYPOINT ["docker-entrypoint.sh"]` with a CMD of `CMD ["php-fpm"]`
# This wrapper script does that, and handles the /data/options.json file
COPY start-optionsjson.py /
ENTRYPOINT ["/start-optionsjson.py"]
CMD ["php-fpm"]
