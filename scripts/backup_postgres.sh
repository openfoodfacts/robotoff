#!/bin/bash
# This script backups PostgreSQL database

set -euo pipefail
IFS=$'\n\t'

echo "Performing Robotoff PostgreSQL backup"

BASE_DIR=/opt/robotoff-backups/postgres
echo "Creating $BASE_DIR if it doesn't exist"
mkdir -p $BASE_DIR

# We backup the two schemas in distinct backups, because the embedding schema is huge
echo "Backing-up public schema..."
# Save the backup in progress in a temporary file so that the latest dump file is always valid
# Wait 10s max for the lock to be released (avoid concurrent dump)
pg_dump --lock-wait-timeout=10000 --schema public -F c -U postgres postgres -f $BASE_DIR/robotoff_postgres_public.dump.tmp
mv $BASE_DIR/robotoff_postgres_public.dump.tmp $BASE_DIR/robotoff_postgres_public.dump
echo "public schema completed"

echo "Backing-up embedding schema..."
pg_dump --lock-wait-timeout=10000 --schema embedding -F c -U postgres postgres -f $BASE_DIR/robotoff_postgres_embedding.dump.tmp
mv $BASE_DIR/robotoff_postgres_embedding.dump.tmp $BASE_DIR/robotoff_postgres_embedding.dump
echo "embedding schema completed"

echo "Backup completed"