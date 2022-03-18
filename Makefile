#!/usr/bin/make

# nice way to have our .env in environment for use in makefile
# see https://lithic.tech/blog/2020-05/makefile-dot-env
# Note: this will mask environment variable as opposed to docker-compose priority
# yet most developper should'nt bump into this
ifneq (,$(wildcard ./.env))
    -include .env
    -include .envrc
    export
endif

NAME = "robotoff"
ENV_FILE ?= .env
MOUNT_POINT ?= /mnt
HOSTS=127.0.0.1 robotoff.openfoodfacts.localhost
DOCKER_COMPOSE=docker-compose --env-file=${ENV_FILE}


.DEFAULT_GOAL := dev
# avoid target corresponding to file names, to depends on them
.PHONY: *

#------#
# Info #
#------#
info:
	@echo "${NAME} version: ${VERSION}"

hello:
	@echo "🥫 Welcome to the Robotoff dev environment setup!"
	@echo "🥫 Note that the first installation might take a while to run, depending on your machine specs."
	@echo "🥫 Typical installation time on 8GB RAM, 4-core CPU, and decent network bandwith is about 2 min."
	@echo "🥫 Thanks for contributing to Robotoff!"
	@echo ""

goodbye:
	@echo "🥫 Cleaning up dev environment (remove containers, remove local folder binds, prune Docker system) …"

#-------#
# Local #
#-------#
dev: hello up create_external_networks
	@echo "🥫 You should be able to access your local install of Robotoff at http://robotoff.openfoodfacts.localhost"

edit_etc_hosts:
	@grep -qxF -- "${HOSTS}" /etc/hosts || echo "${HOSTS}" >> /etc/hosts

#----------------#
# Docker Compose #
#----------------#
up:
	@echo "🥫 Building and starting containers …"
	${DOCKER_COMPOSE} up -d --build 2>&1

down:
	@echo "🥫 Bringing down containers …"
	${DOCKER_COMPOSE} down

hdown:
	@echo "🥫 Bringing down containers and associated volumes …"
	${DOCKER_COMPOSE} down -v

restart:
	@echo "🥫 Restarting frontend & backend containers …"
	${DOCKER_COMPOSE} restart

status:
	@echo "🥫 Getting container status …"
	${DOCKER_COMPOSE} ps

livecheck:
	@echo "🥫 Running livecheck …"
	docker/docker-livecheck.sh

log:
	@echo "🥫 Reading logs (docker-compose) …"
	${DOCKER_COMPOSE} logs -f

#------------#
# Management #
#------------#

# TODO: uncomment once model download CLI is ready 
# dl-models:
# 	@echo "🥫 Downloading models …"
# 	${DOCKER_COMPOSE} run --rm api poetry run robotoff-cli download-models

#------------#
# Quality    #
#------------#
toml-check:
	${DOCKER_COMPOSE} run --rm --no-deps api poetry run toml-sort --check poetry.toml pyproject.toml

toml-lint:
	${DOCKER_COMPOSE} run --rm --no-deps api poetry run toml-sort --in-place poetry.toml pyproject.toml

flake8:
	${DOCKER_COMPOSE} run --rm --no-deps api flake8

black-check:
	${DOCKER_COMPOSE} run --rm --no-deps api black --check .

black:
	${DOCKER_COMPOSE} run --rm --no-deps api black .

mypy:
	${DOCKER_COMPOSE} run --rm --no-deps api mypy .

isort-check:
	${DOCKER_COMPOSE} run --rm --no-deps api isort --check .

isort:
	${DOCKER_COMPOSE} run --rm --no-deps api isort .

docs:
	@echo "🥫 Generationg doc…"
	${DOCKER_COMPOSE} run --rm --no-deps api ./build_mkdocs.sh

checks: toml-check flake8 black-check mypy isort-check docs

lint: toml-lint isort black

tests: create_external_networks unit-tests integration-tests

quality: lint checks tests

health:
	@echo "🥫 Running health tests …"
	@curl --fail --fail-early 127.0.0.1:5500/api/v1/health

unit-tests:
	@echo "🥫 Running tests …"
	# run tests in worker to have more memory
	# also, change project name to run in isolation
	COMPOSE_PROJECT_NAME=robotoff_test ${DOCKER_COMPOSE} run --rm workers poetry run pytest --cov-report xml --cov=robotoff tests/unit 

integration-tests: 
	@echo "🥫 Running integration tests …"
	# run tests in worker to have more memory
	# also, change project name to run in isolation
	COMPOSE_PROJECT_NAME=robotoff_test ${DOCKER_COMPOSE} run --rm workers poetry run pytest -vv --cov-report xml --cov=robotoff --cov-append tests/integration
	( COMPOSE_PROJECT_NAME=robotoff_test ${DOCKER_COMPOSE} down -v || true )

#------------#
# Production #
#------------#
create_external_volumes:
	@echo "🥫 Creating external volumes (production only) …"
	docker volume create api-dataset
	docker volume create postgres-data
	docker volume create es-data

create_external_networks:
	@echo "🥫 Creating external networks if needed … (dev only)"
	( docker network create ${PO_LOCAL_NET} || true )

#---------#
# Cleanup #
#---------#
prune:
	@echo "🥫 Pruning unused Docker artifacts (save space) …"
	docker system prune -af

prune_cache:
	@echo "🥫 Pruning Docker builder cache …"
	docker builder prune -f

clean: goodbye hdown prune prune_cache
