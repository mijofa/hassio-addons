ARG BUILD_FROM
FROM $BUILD_FROM

# Add env
ENV LANG C.UTF-8

#Install snapcast
RUN apk add --no-cache snapcast bash

# Copy data for add-on
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]

FROM kdockerfiles/pulseaudio-shared:13.0-2
LABEL maintainer="KenjiTakahashi <kenji.sx>"

RUN apk add --no-cache \
    libintl \
    libltdl \
    libsndfile \
    speexdsp \
    tdb-libs \
    alsa-lib \
    libcap \
    su-exec

# XXX: Using `29` GID as a workaround for
# RancherOS limitation.
RUN addgroup -S -g 29 pulse && \
    adduser -S -G pulse pulse && \
    addgroup pulse audio && \
    mkdir /tmp/pulse && \
    chown -R pulse:pulse /home/pulse /tmp/pulse

VOLUME ["/tmp/pulse", "/usr/local/etc/pulse"]

COPY pulseaudio-entrypoint.sh /usr/local/bin/

ENTRYPOINT ["pulseaudio-entrypoint.sh"]
CMD ["--log-target=stderr"]
