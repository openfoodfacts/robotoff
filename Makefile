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
ML_OBJECT_DETECTION_MODELS := tf-universal-logo-detector tf-nutrition-table tf-nutriscore
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
dev: hello create-po-default-network build init-elasticsearch migrate-db up create_external_networks
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
	${DOCKER_COMPOSE} logs -f --tail 100 api update-listener scheduler worker_1 worker_2 worker_3 worker_4

#------------#
# Management #
#------------#

dl-models: dl-langid-model dl-object-detection-models dl-category-classifier-model dl-ingredient-detection-model
	@echo "⏬ Downloading all models …"

dl-langid-model:
	@echo "⏬ Downloading language identification model file …"
	mkdir -p models; \
	cd models; \
	wget -cO - https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin > lid.176.bin;

dl-object-detection-models:
	@echo "⏬ Downloading object detection model files …"
	mkdir -p models/triton; \
	cd models/triton; \
	for asset_name in ${ML_OBJECT_DETECTION_MODELS}; \
		do \
			dir=`echo $${asset_name} | sed 's/tf-//g'`; \
			mkdir -p $${dir}/1; \
			wget -cO - https://github.com/openfoodfacts/robotoff-models/releases/download/$${asset_name}-1.0/model.onnx > $${dir}/1/model.onnx; \
	done; \
	mkdir -p nutriscore-yolo/1; \
	wget -cO - https://huggingface.co/openfoodfacts/nutriscore-yolo/resolve/main/weights/best.onnx > nutriscore-yolo/1/model.onnx; \
	mkdir -p nutrition-table-yolo/1; \
	wget -cO - https://huggingface.co/openfoodfacts/nutrition-table-yolo/resolve/8fbcc3d7c442ae5d8f5fca4f99acc19e55d89647/weights/best.onnx > nutrition-table-yolo/1/model.onnx;


dl-category-classifier-model:
	@echo "⏬ Downloading category classifier model files …"
	mkdir -p models/triton; \
	cd models/triton; \
	mkdir -p clip/1; \
	wget -cO - https://github.com/openfoodfacts/robotoff-models/releases/download/clip-vit-base-patch32/model.onnx > clip/1/model.onnx; \
	dir=category-classifier-keras-image-embeddings-3.0/1/model.savedmodel; \
	mkdir -p $${dir}; \
	wget -cO - https://github.com/openfoodfacts/robotoff-models/releases/download/keras-category-classifier-image-embeddings-3.0/saved_model.tar.gz > $${dir}/saved_model.tar.gz; \
	cd $${dir}; \
	tar -xzvf saved_model.tar.gz --strip-component=1; \
	rm saved_model.tar.gz

dl-ingredient-detection-model:
	@echo "⏬ Downloading ingredient detection model files …"
	mkdir -p models/triton; \
	cd models/triton; \
    dir=ingredient-ner/1/model.onnx; \
	mkdir -p $${dir}; \
	wget -cO - https://huggingface.co/openfoodfacts/ingredient-detection/resolve/main/onnx.tar.gz > $${dir}/onnx.tar.gz; \
	cd $${dir}; \
	tar -xzvf onnx.tar.gz --strip-component=1; \
	rm onnx.tar.gz

dl-image-clf-models:
	@echo "⏬ Downloading image classification model files …"
	mkdir -p models/triton; \
	cd models/triton; \
	for asset_name in 'price-proof-classification'; \
		do \
			dir=$${asset_name//-/_}/1; \
			mkdir -p $${dir}; \
			wget -cO - https://huggingface.co/openfoodfacts/$${asset_name}/resolve/main/weights/best.onnx > $${dir}/model.onnx; \
	done;


dl-nutrition-extractor-model:
	@echo "⏬ Downloading nutrition extractor model files …"
	${DOCKER_COMPOSE} run --rm --no-deps api huggingface-cli download openfoodfacts/nutrition-extractor --include 'onnx/*' --local-dir models/triton/nutrition_extractor/1/; \
	cd models/triton/nutrition_extractor/1/; \
	mv onnx model.onnx;

init-elasticsearch:
	@echo "Initializing elasticsearch indices"
	${DOCKER_COMPOSE} up -d elasticsearch 2>&1
	@echo "Sleeping for 20s, waiting for elasticsearch to be ready..."
	@sleep 20
	${DOCKER_COMPOSE} run --rm --no-deps api python -m robotoff init-elasticsearch

launch-burst-worker:
ifdef queues
	${DOCKER_COMPOSE} run --rm -d --no-deps worker_1 python -m robotoff run-worker ${queues} --burst
# Only launch burst worker on low priority queue if queue is not specified
else
	${DOCKER_COMPOSE} run --rm -d --no-deps worker_1 python -m robotoff run-worker robotoff-low --burst
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
	${DOCKER_COMPOSE} run --rm --entrypoint bash --no-deps worker_1 -c "cd i18n && . compile.sh"

update_poetry_lock:
	@echo "🥫  Updating poetry.lock"
	${DOCKER_COMPOSE} run --rm --no-deps api poetry lock --no-update

unit-tests:
	@echo "🥫 Running tests …"
	# run tests in worker to have more memory
	# also, change project name to run in isolation
	${DOCKER_COMPOSE_TEST} run --rm worker_1 poetry run pytest --cov-report xml --cov=robotoff tests/unit ${args}

integration-tests:
	@echo "🥫 Running integration tests …"
	# run tests in worker to have more memory
	# also, change project name to run in isolation
	${DOCKER_COMPOSE_TEST} run --rm worker_1 poetry run pytest -vv --cov-report xml --cov=robotoff --cov-append tests/integration
	( ${DOCKER_COMPOSE_TEST} down -v || true )

ml-tests: 
	@echo "🥫 Running ML tests …"
	${DOCKER_COMPOSE_TEST} up -d triton
	@echo "Sleeping for 30s, waiting for triton to be ready..."
	@sleep 30
	${DOCKER_COMPOSE_TEST} run --rm worker_1 poetry run pytest -vv tests/ml ${args}
	( ${DOCKER_COMPOSE_TEST} down -v || true )

# interactive testings
# usage: make pytest args='test/unit/my-test.py --pdb'
pytest: guard-args
	@echo "🥫 Running test: ${args} …"
	${DOCKER_COMPOSE_TEST} run --rm worker_1 poetry run pytest ${args}

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
