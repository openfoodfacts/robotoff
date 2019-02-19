FROM python:3.7-slim

WORKDIR /opt/robotoff

COPY robotoff.py /opt/robotoff/robotoff.py
COPY robotoff /opt/robotoff/robotoff/
COPY data/taxonomies /opt/robotoff/data/taxonomies
COPY i18n /opt/robotoff/i18n
COPY requirements.txt /opt/robotoff/
COPY gunicorn.conf /opt/robotoff/

RUN pip3 install -r /opt/robotoff/requirements.txt

WORKDIR /opt/robotoff
ENTRYPOINT ["/usr/local/bin/gunicorn", "--config", "/opt/robotoff/gunicorn.conf", "robotoff.app.api:api"]
