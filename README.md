# Robotoff

![Build Status](https://github.com/openfoodfacts/robotoff/workflows/Robotoff%20unit%20tests%20and%20deployments/badge.svg)
[![codecov](https://codecov.io/gh/openfoodfacts/robotoff/branch/master/graph/badge.svg?token=BY2T0KXNO1)](https://codecov.io/gh/openfoodfacts/robotoff)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


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

Once generated, the insights can be applied automatically, or after a manual validation if necessary.
A scheduler regularly marks insights for automatic annotation and sends the update to Open Food Facts.

**Documentation:** <https://openfoodfacts.github.io/robotoff>

**Source code:** <https://github.com/openfoodfacts/robotoff>

**Open Food Facts:** <https://world.openfoodfacts.org>

## Overview

- To get a better understanding on how Robotoff works, go to [Architecture](https://openfoodfacts.github.io/robotoff/introduction/architecture/).
- If you want to help, go to [Contributing](https://openfoodfacts.github.io/robotoff/introduction/contributing/).
- Robotoff can be used as...
  - an [online API](https://openfoodfacts.github.io/robotoff/references/api/)
  - a [CLI tool](https://openfoodfacts.github.io/robotoff/references/cli)
  - a [Python package](https://openfoodfacts.github.io/robotoff/references/package/)
- If you need to deploy or maintain Robotoff, [Maintenance](https://openfoodfacts.github.io/robotoff/how-to-guides/deployment/maintenance) is the way to go.

**NOTE:** This documentation tries to follow as much as possible the documentation system from [Diátaxis](https://diataxis.fr/).

## Licence

Robotoff is licensed under the AGPLv3.
