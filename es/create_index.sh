#!/usr/bin/env bash

INDEX='product'
http PUT http://localhost:9200/${INDEX} < product_index.json
