Robotoff is an API that pulls prediction data, annotation data, product data, nutrition data from MongoDB database in Open Food Facts server.


# This documentation intends to:
1) Familiarize you on running our test cases.
2) Give you some tips from getting stuck if you are working only on Robotoff and don't need complete installation of Open Food Facts server.


> **_NOTE:_** If you are on Windows we recommend using [Git bash](https://git-scm.com/downloads) to run commands.

# How to generate data?
If your development instance is not connected to a product-opener instance (which would automatically happens if you have a running product-opener instance), 
you won't have a mongodb instance, and you wont have any data.
Though you may populate your database with some objects.

We recommend  [Factory](https://factoryboy.readthedocs.io/en/stable/) to create some data in your local database.

If you have installed Robotoff via Docker, you can run Python using Poetry and execute Factory like so:
```
$ docker-compose run --rm api poetry run python
...
> from tests.integration.models_utils import *
> PredictionFactory()
````

Another way to run Factory is to use [PDB](https://docs.python.org/3/library/pdb.html):

```
$ COMPOSE_PROJECT_NAME=robotoff_test docker-compose run --rm workers poetry run pytest --pdb terminal.
```

This will start a PDB console. You can then run your Factory - 
```
(Pdb) from tests.integration.models_utils import *
(Pdb) PredictionFactory()
```

# How to run test cases?
We use [pytest](https://docs.pytest.org/en/7.1.x/) to run test cases and [makefile](../../../robotoff/Makefile) to run our commands. In makefile you will find all the commands used to run Robotoff. 

The following command will run all the test cases one by one:

```
$ COMPOSE_PROJECT_NAME=robotoff_test docker-compose run --rm workers poetry run pytest
```

## How to run a single test case?

You need to specify the name of the test case you want to invoke.

Here is the syntax:

```
$ COMPOSE_PROJECT_NAME=robotoff_test docker-compose run --rm workers poetry run pytest  path/to/test_file.py::the_function_name
```

In this example we call `test_get_type()` from `tests/unit/insights/test_importer.py`

```
$ COMPOSE_PROJECT_NAME=robotoff_test docker-compose run --rm workers poetry run pytest tests/unit/insights/test_importer.py::TestLabelInsightImporter::test_get_type
```

# When to write your own test cases?

Write test cases to test and to understand the working of the function. For example: when you write code to post notifications on Slack channel you can test them only by writing a unit test case. 

There are instances when Robotoff tries to connect to MongoDB via Open Food Facts server. For local testing we do not yet provide a standarized approach to add a MongoDB Docker in the same network and configure Robotoff to use it.

In such cases we recommend either you write a test case of your own or use an existing one. 

To identify when Robotoff connects to MongoDB keep an eye for variables like `server_url`, `server_domain` or `settings.OFF_SERVER_DOMAIN`.

# Debugging

We encourage using PDB to debug. You can add the following lines in your function to find out what your it does and where it breaks.


```
import pdb; pdb.set_trace()
```