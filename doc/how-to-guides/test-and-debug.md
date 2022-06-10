# This documentation intends to:
1) Familiarize you on running our test cases.
2) Give you some tips from getting stuck if you are working only on Robotoff and don't need complete installation of Open Food Facts server.


# How to generate data?

Robotoff is an API that pulls prediction data, annotation data, product data, nutrition data from MongoDB database in Open Food Facts server.


If your development instance is not connected to a product-opener instance 
(which happens automatically if you have a running product-opener instance), 
you won't have a MongoDB instance. This means you won't have any product data on your local set up.
Though you may populate your database with some objects.

We recommend  [Factory](https://factoryboy.readthedocs.io/en/stable/) to create some data in your local database.

If you have installed Robotoff via Docker, you can run Python using Poetry and execute Factory like so:
```
$ docker-compose run --rm api poetry run python
...
> from tests.integration.models_utils import *
> PredictionFactory()
````

> **_NOTE:_** If you are on Windows we recommend using [Git bash](https://git-scm.com/downloads) to run commands.

# How to run test cases?
We use [pytest](https://docs.pytest.org/en/7.1.x/) to run test cases and [Makefile](../../Makefile) to run our commands. In `Makefile` you will find all the commands used to run Robotoff. 

The following command will run all the test cases one by one:

```
$ COMPOSE_PROJECT_NAME=robotoff_test docker-compose run --rm workers poetry run pytest
```

## How to run a single test case?

You need to specify the name of the test case you want to invoke.

Here is the syntax:

```
$ COMPOSE_PROJECT_NAME=robotoff_test docker-compose run --rm workers poetry run pytest path/to/test_file.py::the_function_name
```

In this example we call `test_get_type()` from `tests/unit/insights/test_importer.py`

```
$ COMPOSE_PROJECT_NAME=robotoff_test docker-compose run --rm workers poetry run pytest tests/unit/insights/test_importer.py::TestLabelInsightImporter::test_get_type
```

# When to write your own test cases?

Write test cases every time you write a new feature, to test a feature or to understand the working of an existing function. Automated testing really helps to prevent future bugs as we introduce new features or refactor the code.

There are even cases where automated tests are your only chance to test you code. For example: when you write code to post notifications on Slack channel you can only test them  by writing a unit test case. 

There are instances when Robotoff tries to connect to MongoDB via Open Food Facts server. For local testing we do not yet provide a standarized approach to add a MongoDB Docker in the same network and configure Robotoff to use it.

In such cases you will have to mock the function which calls MongoDB. Feel free to reuse the existing test cases.

To identify parts of the code where Robotoff connects to MongoDB or to Open Food Facts server (the part you should mock), keep an eye for variables like `server_url`, `server_domain` or `settings.OFF_SERVER_DOMAIN`.

# Debugging guide

We encourage using [PDB](https://docs.python.org/3/library/pdb.html)
 to debug. You can add the following lines in your function to find out what your code does and where it breaks.


```
import pdb; pdb.set_trace()
```

and then run the `pytest`, with the `--pdb` option:


```
COMPOSE_PROJECT_NAME=robotoff_test docker-compose run --rm workers poetry run pytest path/to/test.py::test_xxx --pdb
```

Also runnning with `--pdb` flag will stop on every test failure, even if you didn't set any `pdb.set_trace()` this can be a good way to try to understand why a test is failing.
