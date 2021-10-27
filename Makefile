#!/usr/bin/make

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
dev: hello up dl-models init-elasticsearch
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

dl-models:
	@echo "🥫 Downloading models …"
	chmod a+w models
	${DOCKER_COMPOSE} run --rm api poetry run robotoff-cli download-models

init-elasticsearch:
	@echo "Initializing ElasticSearch indexes …"
	${DOCKER_COMPOSE} run --rm api poetry run robotoff-cli init-elasticsearch

#------------#
# Quality    #
#------------#

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

checks: flake8 black-check mypy isort-check

lint: isort black

tests:
	@echo "🥫 Running tests …"
	# run tests in worker to have more memory
	${DOCKER_COMPOSE} run --rm workers poetry run pytest tests

#------------#
# Production #
#------------#
create_external_volumes:
	@echo "🥫 Creating external volumes (production only) …"
	docker volume create api-dataset
	docker volume create postgres-data
	docker volume create es-data

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
