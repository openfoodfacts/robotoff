# base python setup
# -----------------
FROM python:3.7-slim as python-base
RUN apt-get update && \
    apt-get install --no-install-suggests --no-install-recommends -y gettext curl build-essential && \
    apt-get autoremove --purge && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    PYSETUP_PATH="/opt/pysetup" \ 
    VENV_PATH="/opt/pysetup/.venv" \
    POETRY_HOME="/opt/poetry" \
    POETRY_VERSION=1.1.8 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1
ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"

# building packages
# -----------------
FROM python-base as builder-base
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | python3 -
WORKDIR $PYSETUP_PATH
COPY poetry.lock  pyproject.toml poetry.toml ./
RUN poetry install --no-dev

# This is our final image
# ------------------------
FROM python-base as runtime
COPY --from=builder-base $VENV_PATH $VENV_PATH
COPY --from=builder-base $POETRY_HOME $POETRY_HOME
RUN poetry config virtualenvs.create false
ENV POETRY_VIRTUALENVS_IN_PROJECT=false

# create off user
ARG OFF_UID=1000
ARG OFF_GID=$OFF_UID
RUN groupadd -g $OFF_GID off && \
    useradd -u $OFF_UID -g off -m off

COPY --chown=off:off i18n /opt/robotoff/i18n
RUN cd /opt/robotoff/i18n && \
    bash compile.sh
COPY --chown=off:off robotoff /opt/robotoff/robotoff/
COPY --chown=off:off data /opt/robotoff/data
COPY --chown=off:off gunicorn.py /opt/robotoff/

COPY docker/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

COPY --chown=off:off poetry.lock pyproject.toml poetry.toml /opt/robotoff/

USER off
WORKDIR /opt/robotoff
ENTRYPOINT /docker-entrypoint.sh $0 $@
CMD [ "gunicorn", "--config /opt/robotoff/gunicorn.py", "--log-file=-", "robotoff.app.api:api"]


# building dev packages
# ----------------------
FROM builder-base as builder-dev
WORKDIR $PYSETUP_PATH
COPY poetry.lock  pyproject.toml poetry.toml ./
# full install
RUN poetry install

# image with dev tooling
# ----------------------
FROM runtime as runtime-dev
COPY --from=builder-dev $VENV_PATH $VENV_PATH
COPY --from=builder-dev $POETRY_HOME $POETRY_HOME
# Handle possible issue with Docker being too eager after copying files
RUN true
COPY mypy.ini .flake8 pyproject.toml ./
