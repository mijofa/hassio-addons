ARG BUILD_FROM
FROM $BUILD_FROM

# Add env
ENV LANG C.UTF-8

RUN apk add --no-cache snapcast patch pulseaudio-utils \
                       mpd python3

# Fix snapweb to work with https websockets
COPY snapjs.patch /
RUN patch -p0 -i /snapjs.patch

COPY start-optionsjson.py /
#ENTRYPOINT ["/start-optionsjson.py"]
CMD /start-optionsjson.py
