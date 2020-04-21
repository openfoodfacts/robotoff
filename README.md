# Robotoff

[![Build Status](https://travis-ci.org/openfoodfacts/robotoff.svg?branch=master)](https://travis-ci.org/openfoodfacts/robotoff)

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

To have further information in Robotoff architecture, see the wiki's [architecture description](https://github.com/openfoodfacts/robotoff/wiki/Architecture).

The [API documentation](https://github.com/openfoodfacts/robotoff/blob/master/doc/api.md) describes the API endpoints.

For a quickstart of Robotoff as a library, go to the [Quickstart](https://github.com/openfoodfacts/robotoff/blob/master/doc/quickstart.md).

## Installation

Robotoff is made of an API web server, a scheduler, a pool of asynchronous workers and a an Elasticsearch server.
All these services are available as docker images. A `docker-compose.yml` file is used for service orchestration.

To start all services, simply run:

`$ docker-compose up -d`


## Licence

Robotoff is licenced under the AGPLv3.
