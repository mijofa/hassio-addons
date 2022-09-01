ARG BUILD_FROM
FROM $BUILD_FROM

# Add env
ENV LANG C.UTF-8

#Install snapcast
RUN apk add --no-cache snapcast patch pulseaudio-utils

COPY snapjs.patch /
#RUN patch -p0 -i /snapjs.patch

RUN ls -alp /etc/services.d/
RUN rm -rv /etc/services.d/nginx

COPY rootfs /

# # So COPY supports --chown, but not any sort of --mode argument?!?!?
# COPY run.sh /run.sh
# RUN chmod 555 /run.sh
# 
# CMD [ "/run.sh" ]
