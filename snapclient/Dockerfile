ARG BUILD_FROM
FROM $BUILD_FROM

# Add env
ENV LANG C.UTF-8

#Install snapcast
RUN apk add --no-cache snapcast bash

#Add pulseaudio libs
RUN apt-get update && \
    apt-get install -y vlc-nox apt-utils alsa-utils nano pulseaudio && \
    usermod -a -G audio root && \
    usermod -a -G pulse-access root

# Copy data for add-on
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
