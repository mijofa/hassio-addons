FROM hif1/heisenbridge:latest

# Leaving out recomemnds to avoid bringing down and entire kernel & ramdisk
RUN apt update && apt install -y --no-install-recommends wireguard-tools iproute2  python3-yaml && apt clean

# Upstream's ENTRYPOINT is `ENTRYPOINT ["heisenbridge", "-l", "0.0.0.0"]`, but I want to inject Home Assistant's config in before that,
# so I have an alternative entrypoint which will call the CMD afterwards
COPY start-optionsjson.py /
ENTRYPOINT ["/start-optionsjson.py"]
