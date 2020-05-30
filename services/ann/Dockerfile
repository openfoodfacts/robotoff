FROM python:3.7-slim

WORKDIR /opt/ann

COPY *.py /opt/ann/
COPY requirements.txt /opt/ann/

RUN apt-get update && apt-get install --no-install-recommends -y build-essential && pip3 install -r /opt/ann/requirements.txt

WORKDIR /opt/ann
ENTRYPOINT ["/usr/local/bin/gunicorn", "--config", "/opt/ann/gunicorn.py", "api:api"]
