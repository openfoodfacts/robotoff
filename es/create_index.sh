#!/usr/bin/env bash

INDEX='off'
http PUT http://localhost:9200/${INDEX} < index.json
