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
DOCKER_COMPOSE_TEST=COMPOSE_PROJECT_NAME=robotoff_test PO_LOCAL_NET=po_test docker-compose --env-file=${ENV_FILE}
ML_OBJECT_DETECTION_MODELS := tf-universal-logo-detector tf-nutrition-table tf-nutriscore

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
dev: hello build up create_external_networks
	@echo "🥫 You should be able to access your local install of Robotoff at http://localhost:5500"

edit_etc_hosts:
	@grep -qxF -- "${HOSTS}" /etc/hosts || echo "${HOSTS}" >> /etc/hosts

#----------------#
# Docker Compose #
#----------------#
up:
# creates a docker network and runs docker-compose
	@echo "🥫 Building and starting containers …"
	docker network create po_default || true  
ifdef service
	${DOCKER_COMPOSE} up --remove-orphans -d ${service} 2>&1
else
	${DOCKER_COMPOSE} up -d 2>&1
endif

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
	${DOCKER_COMPOSE} logs -f

#------------#
# Management #
#------------#

dl-models: dl-model-labels dl-model-archives dl-model-categorizer

dl-model-archives:
	@echo "🥫 Downloading model archive files …"
	cd models; \
	for asset_name in ${ML_OBJECT_DETECTION_MODELS}; \
		do \
			dir=`echo $${asset_name} | sed 's/tf-//g'`; \
			mkdir -p $${dir} $${dir}/1; \
			wget -cO - https://github.com/openfoodfacts/robotoff-models/releases/download/$${asset_name}-1.0/model.onnx > $${dir}/1/model.onnx; \
	done

dl-model-labels:
	@echo "🥫 Downloading model label files …"
	cd models; \
	for asset_name in ${ML_OBJECT_DETECTION_MODELS}; \
	do \
		dir=`echo $${asset_name} | sed 's/tf-//g'`; \
		mkdir -p $${dir} $${dir}/1; \
		wget -cO - https://github.com/openfoodfacts/robotoff-models/releases/download/$${asset_name}-1.0/labels.txt > $${dir}/labels.txt; \
	done

dl-model-categorizer:
	@echo "🥫 Downloading categorizer model …"
	cd tf_models; \
	dir=category-classifier; \
	mkdir -p $${dir} $${dir}/1; \
	wget -cO - https://github.com/openfoodfacts/robotoff-models/releases/download/keras-category-classifier-xx-2.0/serving_model.tar.gz > $${dir}/1/saved_model.tar.gz; \
	cd $${dir}/1; \
	tar -xzvf saved_model.tar.gz --strip-component=1; \
	rm saved_model.tar.gz

lauch-burst-worker:
ifdef queues
	${DOCKER_COMPOSE} run --rm -d --no-deps worker_low python -m robotoff run-worker ${queues} --burst
else
	${DOCKER_COMPOSE} run --rm -d --no-deps worker_low python -m robotoff run-worker robotoff-low robotoff-high --burst
endif

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

tests: create_external_networks i18n-compile unit-tests integration-tests

quality: lint checks tests

health:
	@echo "🥫 Running health tests …"
	@curl --fail --fail-early 127.0.0.1:5500/api/v1/health

i18n-compile:
	@echo "🥫 Compiling translations …"
# Note it's important to have --no-deps, to avoid launching a concurrent postgres instance
	${DOCKER_COMPOSE} run --rm --entrypoint bash --no-deps worker_high -c "cd i18n && . compile.sh"

unit-tests:
	@echo "🥫 Running tests …"
	# run tests in worker to have more memory
	# also, change project name to run in isolation
	${DOCKER_COMPOSE_TEST} run --rm worker_high poetry run pytest --cov-report xml --cov=robotoff tests/unit

integration-tests:
	@echo "🥫 Running integration tests …"
	# run tests in worker to have more memory
	# also, change project name to run in isolation
	${DOCKER_COMPOSE_TEST} run --rm worker_high poetry run pytest -vv --cov-report xml --cov=robotoff --cov-append tests/integration
	( ${DOCKER_COMPOSE_TEST} down -v || true )

# interactive testings
# usage: make pytest args='test/unit/my-test.py --pdb'
pytest: guard-args
	@echo "🥫 Running test: ${args} …"
	${DOCKER_COMPOSE_TEST} run --rm worker_high poetry run pytest ${args}

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
# for tests
	( docker network create po_test || true )

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