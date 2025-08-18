FROM python:3.11-slim
WORKDIR /app
# The upstream repo has no release tags or versioning branches,
# so I'm just grabbing the commit ID for HEAD at time of writing.
ADD https://github.com/traccar/google-find-hub-sync/archive/dd1682c715e09098ec538cb05343df2af0d36d15.zip \
    /app/google-find-hub-sync.zip

RUN apt-get update && \
    apt-get install --no-install-recommends unzip && \
    apt-get clean && \
    rm -rfv /var/lib/apt/lists/*

RUN unzip -d /app /app/google-find-hub-sync.zip && \
    mv /app/google-find-hub-sync-*/* /app/google-find-hub-sync-*/.??* /app/ &&\
    rmdir /app/google-find-hub-sync-*/ && \
    ln -s /data/secrets.json /app/Auth/secrets.json
RUN pip install --root-user-action=ignore \
                --disable-pip-version-check \
                --no-python-version-warning \
                --no-cache-dir \
                -r /app/requirements.txt \
                paho.mqtt

# # This didn't work because the upstream repo is not structured properly for a Python package
# RUN apt update && apt install --no-install-recommends -y git-core && apt clean
# RUN pip install --no-cache-dir GoogleFindMyTools@git+https://github.com/leonboe1/GoogleFindMyTools@867214fe145587665dc8d8f6c5f94376da5acdf6

COPY hassio-microservice.py .
CMD ["python", "hassio-microservice.py"]
