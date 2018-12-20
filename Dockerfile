FROM python:3.7-slim

WORKDIR /opt/robotoff

COPY robotoff /opt/robotoff/robotoff/
COPY data /opt/robotoff/data/
COPY requirements.txt /opt/robotoff/
COPY gunicorn.conf /opt/robotoff/

RUN pip3 install -r /opt/robotoff/requirements.txt

WORKDIR /opt/robotoff
ENTRYPOINT ["/usr/local/bin/gunicorn", "--config", "/opt/robotoff/gunicorn.conf", "robotoff.app.api:api"]
