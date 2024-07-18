# Dev install

You may choose Docker install (recommended, less chance to mess up with your system, all included) or local install.

## Docker install

After cloning the repository, customize parameters by editing the `.env` file.
You should, consider those changes:

- if you want to use ML models, add `docker/ml.yml` to `COMPOSE_FILE`, using `;` as separator.

  You should also run `make dl-models` to download all machine learning models locally.

- change `OFF_UID` and `OFF_GID` to match your own user UID/GID (optional, only if you experience some file permission issue, see [Getting developper uid for docker](https://gist.github.com/alexgarel/6e6158ee869d6db2192e0441fd58576e))

Note: **beware** not to commit your local changes to `.env` file!

Because of Elasticsearch service, you may need to increase a system parameter (`vm.max_map_count=262144`), as described [here](https://www.elastic.co/guide/en/elasticsearch/reference/current/vm-max-map-count.html).


Then simply run:

```
make dev
```

This will build containers, pull images based containers, create containers and run them.

Verify whether robotoff is running as expected, by executing the following command in CLI:
```bash
curl http://localhost:5500/api/v1/status
```
The expected response is `{"status":"running"}`.

Also take a look at [maintenance](./maintenance.md).

## Local install with poetry

This is an alternative if you are reluctant to use Docker, or have some other reasons to prefer manual install.

After cloning the repository:
1. Make sure a [recent version of Poetry is installed](https://python-poetry.org/docs/#installation)

2. Configure Poetry to use Python 3.11:
   ```bash
   poetry env use python3.11
   ```

3.  Install the dependencies:

    ```bash
    poetry install
    ```

4.  Configure files required for the tests to run locally:

    Compile the i18n files:
    ```bash
    cd i18n && bash compile.sh && cd ..
    ```

3. Also configure your settings to point to your dev postgresql database (that you should have installed the way you want)

4. If you want to use Elasticsearch predictions, you'll also have to set an Elasticsearch instance

5. To debug in a running container, you need to run poetry in the container. For example:

    ```
    docker compose run --rm api poetry run python
    ```
    Here we run the `api` service. This opens a Python command prompt, you may debug with [pdb](https://docs.python.org/3/library/pdb.html) or play with the code. 


## Restore DB dumps

To have real-world data, you're probably interested in restoring data from production server.

### PostgreSQL dump

Robotoff uses PostgreSQL as main database.

First, download the latest DB dump:

```bash
wget https://openfoodfacts.org/data/dumps/robotoff_postgres_latest.dump
```

Start PostgreSQL container and copy the dump inside the container:

```bash
make up service=postgres
docker cp -a robotoff_postgres_latest.dump robotoff_postgres_1:/tmp/
```

Then launch dump restore:


```bash
docker exec -it robotoff_postgres_1 pg_restore -v -d postgres -U postgres -c -j 8 --if-exists /tmp/robotoff_postgres_latest.dump
```

This command drops all existing tables (`-c` command) and perform restore using 8 cores. The database is huge, it may take several hours to run depending on your hardware.

### MongoDB dump

Robotoff also relies on MongoDB to fetch product. On staging and production, it interacts directly with the same MongoDB instance used by Product Opener.

To restore Product Opener MongoDB dump, start by downloading and extracting the archive:

```bash
wget https://static.openfoodfacts.org/data/openfoodfacts-mongodbdump.tar.gz
tar xvzf openfoodfacts-mongodbdump.tar.gz
```

Make sure the MongoDB container is up and running and copy the dump directory inside the container:

```bash
make up service=mongodb
docker cp -a dump robotoff_mongodb_1:/var/tmp/
```

Then launch dump restore:

```bash
docker exec -it robotoff_mongodb_1 mongorestore --drop /var/tmp/dump
```
