#!/usr/bin/make

# nice way to have our .env in environment for use in makefile
# see https://lithic.tech/blog/2020-05/makefile-dot-env
# Note: this will mask environment variable as opposed to docker-compose priority
# yet most developper shouldn't bump into this
ifneq (,$(wildcard ./.env))
    -include .env
    -include .envrc
    export
endif

NAME = "robotoff"
ENV_FILE ?= .env
MOUNT_POINT ?= /mnt
HOSTS=127.0.0.1 robotoff.openfoodfacts.localhost
DOCKER_COMPOSE=docker compose --env-file=${ENV_FILE}
DOCKER_COMPOSE_TEST=COMPOSE_PROJECT_NAME=robotoff_test COMMON_NET_NAME=po_test docker compose --env-file=${ENV_FILE}
# Use bash shell for variable substitution
SHELL := /bin/bash

# Spellcheck
SPELLCHECK_IMAGE_NAME = spellcheck-batch-vllm
SPELLCHECK_TAG = latest
SPELLCHECK_REGISTRY = europe-west9-docker.pkg.dev/robotoff/gcf-artifacts

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
dev: hello create-po-default-network build init-elasticsearch migrate-db download-taxonomies up create_external_networks
	@echo "🥫 You should be able to access your local install of Robotoff at http://localhost:5500"

edit_etc_hosts:
	@grep -qxF -- "${HOSTS}" /etc/hosts || echo "${HOSTS}" >> /etc/hosts

#----------------#
# Docker Compose #
#----------------#
up:
# creates a docker network and runs docker-compose
	@echo "🥫 Building and starting containers …"
ifdef service
	${DOCKER_COMPOSE} up -d ${service} 2>&1
else
	${DOCKER_COMPOSE} up -d 2>&1
endif

# pull images from image repository
pull:
	${DOCKER_COMPOSE} pull

build:
	${DOCKER_COMPOSE} build api 2>&1

down:
	@echo "🥫 Bringing down containers …"
	${DOCKER_COMPOSE} down

hdown:
	@echo "🥫 Bringing down containers and associated volumes …"
	${DOCKER_COMPOSE} down -v

restart:
	@echo "🥫 Restarting containers …"
	${DOCKER_COMPOSE} restart

status:
	@echo "🥫 Getting container status …"
	${DOCKER_COMPOSE} ps

livecheck:
	@echo "🥫 Running livecheck …"
	docker/docker-livecheck.sh

log:
	@echo "🥫 Reading logs (docker-compose) …"
	${DOCKER_COMPOSE} logs -f --tail 100 api update-listener scheduler worker-1 worker-2 worker-3 worker-4 worker-5 worker-6 worker-ml-1 worker-ml-2

#------------#
# Management #
#------------#

dl-langid-model:
	@echo "⏬ Downloading language identification model file …"
	mkdir -p models; \
	cd models; \
	wget -cO - https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin > lid.176.bin;

init-elasticsearch:
	@echo "Initializing elasticsearch indices"
	${DOCKER_COMPOSE} up -d elasticsearch 2>&1
	@echo "Sleeping for 20s, waiting for elasticsearch to be ready..."
	@sleep 20
	${DOCKER_COMPOSE} run --rm --no-deps api python -m robotoff init-elasticsearch

launch-burst-worker:
ifdef queues
	${DOCKER_COMPOSE} run --rm -d --no-deps worker-1 python -m robotoff run-worker ${queues} --burst
# Only launch burst worker on low priority queue if queue is not specified
else
	${DOCKER_COMPOSE} run --rm -d --no-deps worker-1 python -m robotoff run-worker robotoff-low --burst
endif

#------------#
# Quality    #
#------------#
toml-check:
	${DOCKER_COMPOSE} run --rm --no-deps api uv run toml-sort --check pyproject.toml

toml-lint:
	${DOCKER_COMPOSE} run --rm --no-deps api uv run toml-sort --in-place pyproject.toml

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
	@echo "🥫 Generationg docs…"
	${DOCKER_COMPOSE} run --rm --no-deps api ./build_mkdocs.sh

api-lint:
	@echo "🥫 Linting OpenAPI specification…"
	docker run --rm -v ${PWD}:/workspace -w /workspace stoplight/spectral:latest lint docs/references/api.yml --format=pretty

api-lint-check:
	@echo "🥫 Checking OpenAPI specification…"
	docker run --rm -v ${PWD}:/workspace -w /workspace stoplight/spectral:latest lint docs/references/api.yml --fail-severity=error

checks: create_external_networks toml-check flake8 black-check mypy isort-check docs

lint: toml-lint isort black

tests: create_external_networks i18n-compile unit-tests integration-tests

quality: lint checks tests

health:
	@echo "🥫 Running health tests …"
	@curl --fail --fail-early 127.0.0.1:5500/api/v1/health

i18n-compile:
	@echo "🥫 Compiling translations …"
# Note it's important to have --no-deps, to avoid launching a concurrent postgres instance
	${DOCKER_COMPOSE} run --rm --entrypoint bash --no-deps worker-1 -c "cd i18n && . compile.sh"

update_uv_lock:
	@echo "🥫  Updating uv.lock"
	${DOCKER_COMPOSE} run --rm --no-deps api uv lock --no-upgrade

unit-tests:
	@echo "🥫 Running tests …"
	# run tests in worker to have more memory
	# also, change project name to run in isolation
	${DOCKER_COMPOSE_TEST} run --rm worker-1 uv run pytest --cov-report xml --cov=robotoff tests/unit ${args}

integration-tests:
	@echo "🥫 Running integration tests …"
	# run tests in worker to have more memory
	# also, change project name to run in isolation
	${DOCKER_COMPOSE_TEST} run --rm worker-1 uv run pytest -vv --cov-report xml --cov=robotoff --cov-append tests/integration
	( ${DOCKER_COMPOSE_TEST} down -v || true )

ml-tests: 
	@echo "🥫 Running ML tests …"
	${DOCKER_COMPOSE_TEST} up -d triton
	@echo "Sleeping for 30s, waiting for triton to be ready..."
	@sleep 30
	${DOCKER_COMPOSE_TEST} run --rm worker-1 uv run pytest -vv tests/ml ${args}
	( ${DOCKER_COMPOSE_TEST} down -v || true )

# interactive testings
# usage: make pytest args='test/unit/my-test.py --pdb'
pytest: guard-args
	@echo "🥫 Running test: ${args} …"
	${DOCKER_COMPOSE_TEST} run --rm worker-1 uv run pytest ${args}

#------------#
# Production #
#------------#

# Create all external volumes needed for production. Using external volumes is useful to prevent data loss (as they are not deleted when performing docker down -v)
create_external_volumes:
	@echo "🥫 Creating external volumes (production only) …"
	docker volume create robotoff_postgres-data
	docker volume create robotoff_es-data
# In production, robotoff_backup is a NFS mount, this should be created manually in production
	docker volume create robotoff_backup


create_external_networks:
	@echo "🥫 Creating external networks if needed … (dev only)"
	( docker network create ${COMMON_NET_NAME} || true )
# for tests
	( docker network create po_test || true )

# Backup PostgreSQL database in robotoff_backup volume
backup_postgres:
	@echo "🥫 Performing PostgreSQL backup"
	${DOCKER_COMPOSE} exec -t postgres bash /opt/backup_postgres.sh

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

# clean tests, remove containers and volume (useful if you changed env variables, etc.)
clean_tests:
	${DOCKER_COMPOSE_TEST} down -v --remove-orphans

#-----------#
# Utilities #
#-----------#

guard-%: # guard clause for targets that require an environment variable (usually used as an argument)
	@ if [ "${${*}}" = "" ]; then \
   		echo "Environment variable '$*' is mandatory"; \
   		echo use "make ${MAKECMDGOALS} $*=you-args"; \
   		exit 1; \
	fi;

robotoff-cli: guard-args
	${DOCKER_COMPOSE} run --rm --no-deps api python -m robotoff ${args}


# apply DB migrations
migrate-db:
	${DOCKER_COMPOSE} run --rm --no-deps api python -m robotoff migrate-db

download-taxonomies:
	${DOCKER_COMPOSE} run --rm --no-deps api python -m robotoff download-taxonomies --no-download-newer


create-migration: guard-args
	${DOCKER_COMPOSE} run --rm --no-deps api python -m robotoff create-migration ${args}

# create network if not exists
create-po-default-network:
	docker network create po_default || true 

# Spellcheck
build-spellcheck:
	docker build -f batch/spellcheck/Dockerfile -t $(SPELLCHECK_IMAGE_NAME):$(SPELLCHECK_TAG) batch/spellcheck

# Push the image to the registry
push-spellcheck:
	docker tag $(SPELLCHECK_IMAGE_NAME):$(SPELLCHECK_TAG) $(SPELLCHECK_REGISTRY)/$(SPELLCHECK_IMAGE_NAME):$(SPELLCHECK_TAG)
	docker push $(SPELLCHECK_REGISTRY)/$(SPELLCHECK_IMAGE_NAME):$(SPELLCHECK_TAG)

# Build and push in one command
deploy-spellcheck: 
	build-spellcheck push-spellcheck
