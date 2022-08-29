# Test and debug

# This documentation intends to:
1) Familiarize you on running our test cases.
2) Give you some tips from getting stuck if you are working only on Robotoff and don't need complete installation of Open Food Facts server.


# How to generate data?

Robotoff is an API that pulls prediction data, annotation data, product data, nutrition data from MongoDB database in Open Food Facts server.


If your development instance is not connected to a product-opener instance 
(which happens automatically if you have a running product-opener instance),
you won't have a MongoDB instance. This means you won't have any product data on your local set up.
Though you may populate your postgres database with some predictions, insights, images references, etc.

We recommend  [Factory](https://factoryboy.readthedocs.io/en/stable/) to create some data in your local database.

If you have installed Robotoff via Docker, you can run Python using Poetry and execute Factory like so:
```
$ docker-compose run --rm api poetry run python
...
> from tests.integration.models_utils import *
> PredictionFactory()
```

> **NOTE:**  
> If you are on Windows we recommend using [Git bash](https://git-scm.com/downloads) to run commands.

# How to run test cases?
We use [pytest](https://docs.pytest.org/en/7.1.x/) to run test cases and [Makefile](../../Makefile) to run our commands. 

The following command will run all the test cases one by one:

```bash
$ make tests
```

## How to run a single test case?

The simplest is to use the *pytest* make target for that:

```bash
make pytest args='path/to/test_file.py::the_function_name'
```

For example,
to call `test_get_type()` from `tests/unit/insights/test_importer.py`:

```bash
$ make pytest args="tests/unit/insights/test_importer.py::TestLabelInsightImporter::test_get_type"
```

Remember to put quotes especially if you have multiple arguments.


> **NOTE**:  
> Be sure to run `make create_external_networks` before if needed (especially if you get `Network po_test declared as external, but could not be found`)



# When to write your own test cases?

Write test cases every time you write a new feature, to test a feature or to understand the working of an existing function. Automated testing really helps to prevent future bugs as we introduce new features or refactor the code.

There are even cases where automated tests are your only chance to test you code. For example: when you write code to post notifications on Slack channel you can only test them  by writing a unit test case. 

There are instances when Robotoff tries to connect to MongoDB via Open Food Facts server. For local testing we do not yet provide a standarized approach to add a MongoDB Docker in the same network and configure Robotoff to use it.

In such cases you will have to mock the function which calls MongoDB. Feel free to reuse the existing test cases.

To identify parts of the code where Robotoff connects to MongoDB or to Open Food Facts server (the part you should mock), keep an eye for variables like `server_url`, `server_domain` or `settings.OFF_SERVER_DOMAIN`.

# Debugging guide

We encourage using [PDB](https://docs.python.org/3/library/pdb.html)
to debug.

Running test with `--pdb` flags, pytest will stop and open the pdb console as soon as there is an error or an assert fails.
This can be a good way to try to understand why a test is failing.


```bash
make pytest args="path/to/test.py --pdb"
```
If it's a `mock.assert_called_with`, you can look at the real data passed to a test case by calling mock.call_args in the pdb console.

If you need more precise control to see code path before it breaks, you can add the following lines in your function to find out what your code does and where it breaks.

```python
import pdb; pdb.set_trace()
```

and then run the `pytest`, with the `--pdb` option (as above).

> **Note**  
> we need the `--pdb` option,
to view the inputs and outputs captured by pytest
> and access the pdb console.

