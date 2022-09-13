ARG BUILD_FROM
FROM $BUILD_FROM

# Add env
ENV LANG C.UTF-8

RUN apk add --no-cache snapcast patch pulseaudio-utils \
                       mpd python3 && \
    setcap -r /usr/bin/mpd  # Docker containers don't get cap_sys_nice by default, so tell mpd not to try

# Fix snapweb to work with https websockets
COPY snapjs.patch /
RUN patch -p0 -i /snapjs.patch

COPY start-optionsjson.py /
ENTRYPOINT ["/start-optionsjson.py"]
