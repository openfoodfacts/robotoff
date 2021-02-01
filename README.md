# Robotoff

![Build Status](https://github.com/openfoodfacts/robotoff/workflows/Robotoff%20unit%20tests%20and%20deployments/badge.svg)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Robotoff is a service managing potential Open Food Facts updates (also known as _insights_).
These insights include a growing set of facts, including:
- the product category, weight, brand, packager codes and expiration date
- some of its labels
- abusive pictures (selfies)
- rotated pictures
- ingredient spellchecking

Robotoff provides an API to:
- Fetch insights
- Annotate an insight (accept or reject) and send the update to Open Food Facts if the insight was accepted

Once generated, the insights can be applied automatically, or after a manual validation if needs be.
A scheduler takes care of regularly marking insights for automatic annotation and for sending the update to Open Food Facts.

To have further information about Robotoff, go to the [Wiki](https://github.com/openfoodfacts/robotoff/wiki).

The [API documentation](https://github.com/openfoodfacts/robotoff/blob/master/doc/api.md) describes the API endpoints.

## Installation

Robotoff is made of an API web server, a scheduler, a pool of asynchronous workers and a an Elasticsearch server.
All these services are available as docker images. A `docker-compose.yml` file is used for service orchestration.

Before launching the Elasticsearch service, you may need to increase a system parameter (`vm.max_map_count=262144`), as described [here](https://stackoverflow.com/questions/51445846/elasticsearch-max-virtual-memory-areas-vm-max-map-count-65530-is-too-low-inc).

To start all services, simply run:

`$ docker-compose up -d`

## Roadmap
- 
- 
- 

## Licence

Robotoff is licenced under the AGPLv3.
