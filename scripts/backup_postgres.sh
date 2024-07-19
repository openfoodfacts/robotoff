#!/bin/bash
# This script backups PostgreSQL database

set -euo pipefail
IFS=$'\n\t'

echo "$(date -u '+%Y-%m-%d %H:%M:%S') :: Performing Robotoff PostgreSQL backup"

BASE_DIR=/opt/robotoff-backups/postgres
echo "$(date -u '+%Y-%m-%d %H:%M:%S') :: Creating $BASE_DIR if it doesn't exist"
mkdir -p $BASE_DIR

# We backup the two schemas in distinct backups, because the embedding schema is huge
# Save the backup in progress in a temporary file so that the latest dump file is always valid
# Wait 10s max for the lock to be released (avoid concurrent dump)
pg_dump --lock-wait-timeout=10000 -F c -U postgres robotoff -f $BASE_DIR/robotoff_postgres.dump.tmp
mv $BASE_DIR/robotoff_postgres.dump.tmp $BASE_DIR/robotoff_postgres.dump
echo "$(date -u '+%Y-%m-%d %H:%M:%S') :: back-up completed"
