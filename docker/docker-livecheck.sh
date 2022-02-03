#!/bin/sh

ENV_FILE="${ENV_FILE:-.env}"
RET_CODE=0
for service in `docker-compose --env-file=${ENV_FILE} config  --service | tr '\n' ' '`; do 
    found=$(docker-compose --env-file=${ENV_FILE} ps -- ${service}|grep  ${service}_1|grep '\bUp\b')
    if [ -z "$found" ] 
    then
        echo "$service: DOWN"
        RET_CODE=1
    else
        echo "$service: UP"
    fi
done;
exit $RET_CODE;
