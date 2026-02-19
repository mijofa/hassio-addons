ARG BUILD_FROM
FROM $BUILD_FROM

# Add env
ENV LANG C.UTF-8

RUN apk add --no-cache snapcast pulseaudio-utils \
                       patch unzip \
                       mpd python3

# FIXME: We're using a very old version of Snapweb because:
#        * I want autoplay: https://github.com/snapcast/snapweb/issues/159 & https://github.com/snapcast/snapweb/pull/160
#        * I want to use relative websocket paths with the patch below: https://github.com/snapcast/snapweb/issues/109
ADD https://github.com/snapcast/snapweb/releases/download/v0.5.0/snapweb.zip /tmp/snapweb.zip
RUN unzip -od /usr/share/snapserver/snapweb/ /tmp/snapweb.zip

# Fix snapweb to work with https websockets
COPY snapjs.patch /
RUN patch -p0 -i /snapjs.patch

RUN apk add --no-cache spotifyd ; \
    mkdir /var/cache/spotifyd ; \
    ln -s /data/spotify-zeroconf /var/cache/spotifyd/zeroconf ; \
    ln -s /data/spotify-oauth /var/cache/spotifyd/oauth

COPY start-optionsjson.py /
#ENTRYPOINT ["/start-optionsjson.py"]
CMD /start-optionsjson.py
