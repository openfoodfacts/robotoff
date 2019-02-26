#!/usr/bin/env bash

http PUT http://localhost:9200/product < product_index.json
http PUT http://localhost:9200/category < category_index.json
