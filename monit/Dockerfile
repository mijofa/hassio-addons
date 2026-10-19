# NOTE: This is based on https://github.com/MMonit/monit-docker-test/blob/9499e067e6ad9bc54be2d15ac16dc430619dcd5d/Dockerfile
# FIXME: Use newer Debian? Or Alpine because that's what HA usually uses?
FROM debian:trixie-slim

# NOTE: This Dockerfile builds Monit from source for testing purposes.
# For production use, download a pre-built Monit binary to significantly reduce
# the container size and avoid including build dependencies. Consider using
# Alpine Linux as the base image for even smaller containers.
# See https://mmonit.com/monit/#download
# FIXME: DO ^ that

# Install necessary packages for building Monit (SSL and Pam are optional)
RUN apt-get update && \
    apt-get install -y \
    zlib1g-dev \
    libpam0g-dev \
    libssl-dev \
    libtool \
    bison \
    flex \
    autoconf \
    gcc \
    make \
    git \
    procps \
    python3 \
    && rm -rf /var/lib/apt/lists/*

# Clone and build the latest Monit
WORKDIR /tmp
RUN git clone https://github.com/MMonit/monit.git && \
    cd monit && \
    ./bootstrap && \
    ./configure && \
    make && \
    make install && \
    cd .. && \
    rm -rf monit

# # Create directories
# RUN mkdir -p /var/lib/monit /usr/local/bin /var/log
# 
# # Copy the test scripts
# COPY scripts/program.sh /usr/local/bin/
# COPY scripts/process.sh /usr/local/bin/
# COPY scripts/check_zombies.sh /usr/local/bin/
# COPY monitrc /etc/monitrc
# 
# # Set proper permissions for monitrc (required by Monit)
# RUN chmod 600 /etc/monitrc
# 
# # Make scripts executable
# RUN chmod +x /usr/local/bin/*.sh
# 
# # Create a directory for result files
# RUN mkdir -p /results
# 
# # Expose port if you want to use the web interface
# EXPOSE 2812

# # Set Monit as the entrypoint (PID 1)
# ENTRYPOINT ["/usr/local/bin/monit", "-I", "-c", "/data/monitrc"]

COPY start-optionsjson.py /
ENTRYPOINT ["/start-optionsjson.py"]
