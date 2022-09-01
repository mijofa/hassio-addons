ARG BUILD_FROM
FROM $BUILD_FROM

# Add env
ENV LANG C.UTF-8

# I don't need nginx
RUN apk del nginx
RUN rm -rv /etc/services.d/nginx

# Gah shit, maybe I was better off just starting from scratch and redoing the VLC stuff
# Snapserver in this version of Alpine is too old, but this version of Alpine is old so just upgrade
RUN apk update && apk upgrade && \
    sed -i 's/v3.13/v3.16/' /etc/apk/repositories && \
    apk upgrade --available && \
    sed -i 's/geteuid/getppid/' /usr/bin/vlc
# This last sed is already in upstream's Dockerfile, it's shit and should be fixed better (don't run VLC as root)
# but the Alpine upgrade blows it away, so for now I'm just putting it back

#Install snapcast
RUN apk add --no-cache snapcast patch pulseaudio-utils

# Fix snapweb to work with https websockets
COPY snapjs.patch /
RUN patch -p0 -i /snapjs.patch

COPY rootfs /
