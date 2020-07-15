FROM python:3.7-slim

WORKDIR /opt/ann

RUN apt-get update && \
    apt-get install --no-install-suggests --no-install-recommends -y build-essential && \
    apt-get autoremove --purge && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY *.py /opt/ann/
COPY requirements.txt /opt/ann/
RUN pip3 install --no-cache-dir -r /opt/ann/requirements.txt

WORKDIR /opt/ann
ENTRYPOINT ["/usr/local/bin/gunicorn", "--config", "/opt/ann/gunicorn.py", "api:api"]
