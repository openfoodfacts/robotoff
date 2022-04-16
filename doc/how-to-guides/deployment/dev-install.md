# Dev install

You may choose Docker install (recommended, less chance to mess up with your system, all included) or local install.

## Docker install

After cloning the repository,
customize parameters by editing the `.env` file.
You should, consider those changes:

- if you want to use tensorflow models, add `docker/ml.yml` to `COMPOSE_FILE`
- change `OFF_UID` and `OFF_GID` to match your own user UID/GID.
  (see [Getting developper uid for docker](https://gist.github.com/alexgarel/6e6158ee869d6db2192e0441fd58576e))

Note: **beware** not to commit your changes in the future.

Because of Elasticsearch service, you may need to increase a system parameter (`vm.max_map_count=262144`), as described [here](https://www.elastic.co/guide/en/elasticsearch/reference/current/vm-max-map-count.html).


Then simply run:

```
make dev
```

This will build containers, pull images based containers, create containers and run them.
It will also download models.

Also take a look at [maintenance](./maintenance.md)

## Local install with poetry

This is an alternative if you are reluctant to use Docker, or have some other reasons to prefer manual install.

After cloning the repository:

1.  Install the dependencies using [Poetry](https://python-poetry.org/docs/#installation):

    ```
    poetry install
    ```

2.  Configure files required for the tests to run locally:

    Compile the i18n files:
    ```
    cd i18n && bash compile.sh && cd ..
    ```

3. Also configure your settings to point to your dev postgresql database (that you should have installed the way you want)

4. If you want to use Elasticsearch predictions, you'll also have to set an Elasticsearch instance

5. To configure MongoDB for docker, start with installing [official MongoDB image](https://hub.docker.com/_/mongo)

    Start the MongoDB container with

    ```
    docker start mongodb
    ```

    Your MongoDB has been installed sucessfully  and is up and running. Congratulations!

    Once you have the Robotoff services running with `docker-compose up` along with MongoDB container, proceed with the next steps.

    Our MongoDB does not have a database right now. So we restore it.

    ```
    tar xzf off-dev-mongo-dump.tar.gz
    docker cp -a dump robotoff_mongodb_1:/var/tmp/
    docker exec mongodb mongorestore /var/tmp/dump

    ```

    First we have extracted the zip file. Next we copy the dump in our running MongoDB service in Robotoff `robotoff_mongodb_1`. Lastly, we restore the dump from Robotoff's service to `mongodb` container.

    The MongoDB configuration is now compelete. 

    You can now work with Robotoff seamlessly.


6. To debug in a running container, you need to run poetry in the container. For example:

    ```
    docker-compose run --rm api poetry run python
    ```
    Here we run the `api` service. This opens a Python command prompt, you may debug with [pdb)\](https://docs.python.org/3/library/pdb.html) or play with the code. 
