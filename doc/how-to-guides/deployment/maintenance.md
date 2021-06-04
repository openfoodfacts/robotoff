# Services maintenance

Robotoff is split in 3 services:

- the _scheduler_, responsible for launching recurrent tasks (downloading new dataset, processing insights automatically,...)
- the _workers_, responsible for all long-lasting tasks (mainly insight extraction from images)
- the public _api_ service

Two additional services are used:

- a PostgreSQL database (_postgres_ service)
- a Elasticsearch single node (_elasticsearch_ service)

All services are managed by docker. [docker-compose](https://docs.docker.com/compose/) is used to manage these services.

## Quick start

### Run docker-compose

Before launching the Elasticsearch service, you may need to increase a system parameter (`vm.max_map_count=262144`), as described [here](https://stackoverflow.com/questions/51445846/elasticsearch-max-virtual-memory-areas-vm-max-map-count-65530-is-too-low-inc).

To start all services, simply run:

```sh
docker-compose up -d
```

### Monitor

To display all running services, run `docker ps`:

```
CONTAINER ID        IMAGE                       COMMAND                  CREATED             STATUS              PORTS                                                NAMES
faf7c9b029ce        openfoodfacts/robotoff      "python3 -m robotoff…"   22 minutes ago      Up 22 minutes                                                            robotoff_scheduler_1
00bfe5e8b67e        openfoodfacts/robotoff      "python3 -m robotoff…"   32 minutes ago      Up 32 minutes                                                            robotoff_workers_1
9d7d357bbe2a        openfoodfacts/robotoff      "/usr/local/bin/guni…"   33 minutes ago      Up 33 minutes                                                            robotoff_api_1
60dc39032386        raphael0202/elasticsearch   "/usr/local/bin/dock…"   5 weeks ago         Up 5 weeks          127.0.0.1:9200->9200/tcp, 127.0.0.1:9300->9300/tcp   robotoff_elasticsearch_1
64b9b2f6ecb8        postgres:11.2-alpine        "docker-entrypoint.s…"   5 weeks ago         Up 5 days           127.0.0.1:5432->5432/tcp                             robotoff_postgres_1
```

To display all containers (even stopped ones), add the `--all` flag.

To stop the scheduler service, run `docker stop robotoff_scheduler_1`.
To start it again, `docker start robotoff_scheduler_1`.

To display the logs of the container, `docker logs robotoff_scheduler_1`.
Two options are often used: `-f` to follow output and `--tail n` to only display last n lines.
