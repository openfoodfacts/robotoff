FROM python:3.7-slim

WORKDIR /opt/robotoff

COPY robotoff /opt/robotoff/robotoff/
COPY data /opt/robotoff/data
COPY i18n /opt/robotoff/i18n
COPY pyproject.toml poetry.lock poetry.toml /opt/robotoff/
COPY gunicorn.py /opt/robotoff/

RUN apt-get update && \
    apt-get install --no-install-suggests --no-install-recommends -y gettext curl && \
    apt-get autoremove --purge && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN cd /opt/robotoff/i18n && \
    bash compile.sh

WORKDIR /opt/robotoff

# Restrict poetry version to 1.1.7, as newer version cause issues with 'docker pull' on the server.
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | POETRY_VERSION=1.1.7 python -

RUN /root/.poetry/bin/poetry config virtualenvs.create false
RUN /root/.poetry/bin/poetry install --no-dev

ENTRYPOINT ["/usr/local/bin/gunicorn", "--config", "/opt/robotoff/gunicorn.py", "robotoff.app.api:api"]
