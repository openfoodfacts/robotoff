# Services maintenance

Robotoff is split in several services:

- the _scheduler_, responsible for launching recurrent tasks (downloading new dataset, processing insights automatically,...)
- the _workers_, responsible for all long-lasting tasks (mainly insight extraction from images)
- the public _api_ service
- the _tf\_serving_ service which serve tensor flow models

Two additional services are used:

- a PostgreSQL database (_postgres_ service)
- a Elasticsearch single node (_elasticsearch_ service)

All services are managed by docker. [docker-compose](https://docs.docker.com/compose/) is used to manage these services.

`tf-serving` has it's own file: `docker/ml.yml`.

Models for tf-serving part are stored as released at https://github.com/openfoodfacts/robotoff-models.


## Quick start

see [dev-install](./dev-install.md)

You can then use:
`docker-compose start [service-name]` or `docker-compose stop [service-name]`

Or `make up` when you refresh the product (it will re-build and run `docker-compose up -d`).

Take the time to become a bit familiar with docker-compose if it's your first use.

## Monitor

To display the logs of the container, `docker-compose logs [service-name]`.
(without service-name, you got all logs).

Two options are often used: `-f` to follow output and `--tail n` to only display last n lines.

To display all running services, run `docker-compose ps`:

```
        Name                      Command               State                  Ports                
----------------------------------------------------------------------------------------------------
robotoff_api_1         /bin/sh -c /docker-entrypo ...   Up      0.0.0.0:5500->5500/tcp,:::5500->5500
                                                                /tcp                                
robotoff_postgres_1    docker-entrypoint.sh postg ...   Up      127.0.0.1:5432->5432/tcp            
robotoff_scheduler_1   /bin/sh -c /docker-entrypo ...   Up                                          
robotoff_workers_1     /bin/sh -c /docker-entrypo ...   Up                              
```

