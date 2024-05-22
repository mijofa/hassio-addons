FROM hif1/heisenbridge:1.14.6

RUN apk add py3-yaml

# Built in entrypoint doesn't really support Home Assistant's config system,
# This wrapper script handles reading /data/options.json and running the entrypoint accordingly
COPY start-optionsjson.py /
ENTRYPOINT ["/start-optionsjson.py"]
CMD []
