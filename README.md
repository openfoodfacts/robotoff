# Robotoff

![Build Status](https://github.com/openfoodfacts/robotoff/workflows/Robotoff%20unit%20tests%20and%20deployments/badge.svg)
[![codecov](https://codecov.io/gh/openfoodfacts/robotoff/branch/master/graph/badge.svg?token=BY2T0KXNO1)](https://codecov.io/gh/openfoodfacts/robotoff)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Documentation:** <https://openfoodfacts.github.io/robotoff>

**Source code:** <https://github.com/openfoodfacts/robotoff>

**Open Food Facts:** <https://world.openfoodfacts.org>

Robotoff is a service managing potential Open Food Facts updates (also known as _insights_).
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

## Overview

- To get a better understanding on how Robotoff works, go to [Architecture](./introduction/architecture).
- If you want to help, go to [Contributing](./introduction/contributing). In particular, to make to project run, go to [Get started!](./introduction/contributing#get-started)
- Robotoff can be used as...
  - an [online API](./references/api.md)
  - a [CLI tool](./references/cli.md)
  - a [Python package](./references/package.md)
- If you need to deploy or maintain Robotoff, [Maintenance](./how-to-guides/deployment/maintenance) is the way to go.

**NOTE:** This documentation tries to follow as much as possible the documentation system from [Divio](https://documentation.divio.com/).

## Licence

Robotoff is licensed under the AGPLv3.
