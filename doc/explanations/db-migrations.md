# Database migrations

We use [peewee_migrate](https://github.com/klen/peewee_migrate) to handle our SQL database migrations.

## Create a migration

You should create a migration if you update the SQL database schema.
To create a new migration, use:

`make robotoff-cli args='create-migration MIGRATION_NAME --auto'`

You should use an identifiable name (such as "add_bounding_box") to the migration.

The `--auto` flag is used to ask `peewee_migrate` to scan all table definitions in the source code and create the migration file
automatically. You can skip it if you want `peewee_migrate` to create a blank migration file.


## Apply the migration

To apply all pending migrations, use:

`make migrate-db`


## What if I had a previous installation of Robotoff with an initialized DB?

You should then create yourself the migration table:

```sql
CREATE TABLE IF NOT EXISTS "migratehistory"
(
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "migrated_at" TIMESTAMP NOT NULL
)
```

Then add manually the the initial migration file in database:

```sql
INSERT INTO "migratehistory" VALUES (1, '001_initial', CURRENT_TIMESTAMP);
```

Then you can apply remaining migrations with `make migrate-db`.