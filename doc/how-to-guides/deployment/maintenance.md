# Services maintenance

Robotoff is split in several services:

- the _scheduler_, responsible for launching recurrent tasks (downloading new dataset, processing insights automatically,...)
- the _workers_, responsible for all long-lasting tasks (mainly insight extraction from images)
- the public _api_ service
- the _triton_ service which serve ML models

Two additional services are used:

- a PostgreSQL database (_postgres_ service)
- a Elasticsearch single node (_elasticsearch_ service)

All services are managed by docker. [docker-compose](https://docs.docker.com/compose/) is used to manage these services.

`tf-serving` and `triton` have their own file: `docker/ml.yml`.

ML models are stored as released at https://github.com/openfoodfacts/robotoff-models.

All Robotoff services are running on one of the two Docker instances (OVH 200 VM for staging and OVH 201 VM for production). You should use the proxy servers ([ovh1.openfoodfacts.org]() or [ovh2.openfoofacts.org]()) to reach these instances. You can get more information on Docker VMs [here](https://github.com/openfoodfacts/openfoodfacts-infrastructure/blob/develop/docs/docker_architecture.md).


## Quick start

see [dev-install](./dev-install.md)

You can then use:
`docker compose start [service-name]` or `docker compose stop [service-name]`

Or `make up` when you refresh the product (it will re-build and run `docker compose up -d`).

Take the time to become a bit familiar with docker-compose if it's your first use.

## Monitor

### See logs

To display the logs of the container, `docker compose logs [service-name]`.
(without service-name, you got all logs).

Two options are often used: `-f` to follow output and `--tail n` to only display last n lines.

To display all running services, run `make status`:

```
        Name                      Command               State                  Ports                
----------------------------------------------------------------------------------------------------
robotoff_api_1         /bin/sh -c /docker-entrypo ...   Up      0.0.0.0:5500->5500/tcp,:::5500->5500
                                                                /tcp                                
robotoff_postgres_1    docker-entrypoint.sh postg ...   Up      127.0.0.1:5432->5432/tcp            
robotoff_scheduler_1   /bin/sh -c /docker-entrypo ...   Up                                          
robotoff_worker_low_1     /bin/sh -c /docker-entrypo ...   Up                              
robotoff_worker_high_1     /bin/sh -c /docker-entrypo ...   Up
...                              
```

### See number of tasks in queues

If you want to monitor how much job robotoff has to do (how behind it is),
you can run the `rq` command to get status:

```bash
docker compose run --rm --no-deps worker_1 rq info
```

This may help you understand why robotoff insight are not visible immediately on products.

See also [rq monitoring documentation](https://python-rq.org/docs/monitoring/) for more commands and informations.

## Database backup and restore

To backup the PostgreSQL database, run the following command:

```bash
docker exec -i robotoff_postgres_1 pg_dump --schema public -F c -U postgres postgres | gzip > robotoff_postgres_$(date +%Y-%m-%d).dump
```

All Robotoff PostgreSQL dumps are stored on _openfoodfacts.org_ server, in `/srv2/off/html/data/dumps` folder. When backing up the database, please update the `robotoff_postgres_latest.dump` symlink so that http://openfoodfacts.org/data/dumps/robotoff_postgres_latest.dump always points to the latest dump.

You can restore it easily by copying the dump file inside the container and launching `pg_restore`:

```bash
docker cp -a robotoff_postgres.dump robotoff_postgres_1:/tmp/
docker exec -it robotoff_postgres_1 pg_restore -v -d postgres -U postgres -j 8 --if-exists /tmp/robotoff_postgres.dump
```
