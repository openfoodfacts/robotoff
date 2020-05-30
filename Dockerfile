FROM python:3.7-slim

WORKDIR /opt/robotoff

COPY robotoff /opt/robotoff/robotoff/
COPY data /opt/robotoff/data
COPY i18n /opt/robotoff/i18n
COPY requirements.txt /opt/robotoff/
COPY gunicorn.py /opt/robotoff/

RUN pip3 install -r /opt/robotoff/requirements.txt && apt-get update && apt-get install -y gettext && cd /opt/robotoff/i18n && bash compile.sh

WORKDIR /opt/robotoff
ENTRYPOINT ["/usr/local/bin/gunicorn", "--config", "/opt/robotoff/gunicorn.py", "robotoff.app.api:api"]
