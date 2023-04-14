# Robotoff

![Build Status](https://github.com/openfoodfacts/robotoff/workflows/Robotoff%20unit%20tests%20and%20deployments/badge.svg)
[![codecov](https://codecov.io/gh/openfoodfacts/robotoff/branch/master/graph/badge.svg?token=BY2T0KXNO1)](https://codecov.io/gh/openfoodfacts/robotoff)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
![GitHub language count](https://img.shields.io/github/languages/count/openfoodfacts/robotoff)
![GitHub top language](https://img.shields.io/github/languages/top/openfoodfacts/robotoff)
![GitHub last commit](https://img.shields.io/github/last-commit/openfoodfacts/robotoff)
![Github Repo Size](https://img.shields.io/github/repo-size/openfoodfacts/robotoff)

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://static.openfoodfacts.org/images/logos/off-logo-horizontal-dark.png?refresh_github_cache=1">
  <source media="(prefers-color-scheme: light)" srcset="https://static.openfoodfacts.org/images/logos/off-logo-horizontal-light.png?refresh_github_cache=1">
  <img height="48" src="https://static.openfoodfacts.org/images/logos/off-logo-horizontal-light.svg">
</picture>

**Robotoff** is a service managing potential Open Food Facts updates (also known as _insights_) and predictions (which can then be combined to generate an insight).
These insights include a growing set of facts, including:

- the product category, weight, brand, packager codes and expiration date
- some of its labels
- abusive pictures (selfies)
- rotated pictures
- ingredient spellchecking

Robotoff provides an API to:

- Fetch insights
- Annotate an insight (accept or reject)

Once generated, the insights can be applied automatically, or after a manual validation if necessary. A scheduler regularly marks insights for automatic annotation and sends the update to Open Food Facts.

A detailed description of [how predictions and insights work is available here](https://openfoodfacts.github.io/robotoff/robotoff/explanations/predictions/).

Robotoff works together with [Product Opener](https://github.com/openfoodfacts/openfoodfacts-server), the Core server of Open Food Facts (in Perl, which can also be installed locally using Docker) and the [Open Food Facts apps](https://github.com/openfoodfacts/smooth-app) (which can work with your local instance after enabling dev mode)

**Documentation:** <https://openfoodfacts.github.io/robotoff>

**Source code:** <https://github.com/openfoodfacts/robotoff>

**Open Food Facts:** <https://world.openfoodfacts.org>

## Overview

- To get a better understanding on how Robotoff works, go to [Architecture](https://openfoodfacts.github.io/robotoff/introduction/architecture/).
- If you want to help, go to [Contributing](https://openfoodfacts.github.io/robotoff/introduction/contributing/).
- Robotoff can be used as...
  - an [online API](https://openfoodfacts.github.io/robotoff/references/api/)
  - a CLI tool
  - a [Python package](https://openfoodfacts.github.io/robotoff/references/package/)
- If you need to deploy or maintain Robotoff, [Maintenance](https://openfoodfacts.github.io/robotoff/how-to-guides/deployment/maintenance) is the way to go.

**NOTE:** This documentation tries to follow as much as possible the documentation system from [Diátaxis](https://diataxis.fr/).

## Licence

Robotoff is licensed under the AGPLv3.

## Weekly meetings
- We e-meet every Tuesday at 11:00 Paris Time (10:00 London Time, 15:30 IST, 02:00 AM PT)
- ![Google Meet](https://img.shields.io/badge/Google%20Meet-00897B?logo=google-meet&logoColor=white) Video call link: https://meet.google.com/qvv-grzm-gzb
- Join by phone: https://tel.meet/qvv-grzm-gzb?pin=9965177492770
- Add the Event to your Calendar by [adding the Open Food Facts community calendar to your calendar](https://wiki.openfoodfacts.org/Events)
- [Weekly Agenda](https://drive.google.com/open?id=1RUfmWHjtFVaBcvQ17YfXu6FW6oRFWg-2lncljG0giKI): please add the Agenda items as early as you can. Make sure to check the Agenda items in advance of the meeting, so that we have the most informed discussions possible. 
- The meeting will handle Agenda items first, and if time permits, collaborative bug triage.
- We strive to timebox the core of the meeting (decision making) to 30 minutes, with an optional free discussion/live debugging afterwards.
- We take comprehensive notes in the Weekly Agenda of agenda item discussions and of decisions taken.

## Contributors

<a href="https://github.com/openfoodfacts/robotoff/graphs/contributors">
  <img alt="List of contributors to this repository" src="https://contrib.rocks/image?repo=openfoodfacts/robotoff" />
</a>

