FROM python:3.7-slim

WORKDIR /opt/robotoff

COPY robotoff /opt/robotoff/robotoff/
COPY data /opt/robotoff/data
COPY i18n /opt/robotoff/i18n
COPY requirements.txt /opt/robotoff/
COPY gunicorn.py /opt/robotoff/

RUN apt-get update && \
    apt-get install --no-install-suggests --no-install-recommends -y gettext && \
    apt-get autoremove --purge && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    cd /opt/robotoff/i18n && \
    bash compile.sh

RUN pip3 install --no-cache-dir -r /opt/robotoff/requirements.txt

WORKDIR /opt/robotoff
ENTRYPOINT ["/usr/local/bin/gunicorn", "--config", "/opt/robotoff/gunicorn.py", "robotoff.app.api:api"]
