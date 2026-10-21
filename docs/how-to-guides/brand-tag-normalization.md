# Proposed brand tag normalization

This is a proposed Robotoff-side solution for issue #1535. Maintainers still
need to agree in that issue that normalization belongs here before merging
or deploying it.

Brand predictions are normalized before duplicate detection and insertion.
Brand insight candidates use the same canonical `xx:` form. Existing
namespaces, empty strings and null values are preserved. Display names in
`value` are unchanged. Blacklist and barcode-range validation accepts either
format in existing resource files.

Migration `010_normalize_brand_value_tags` updates `prediction.value_tag`
and `product_insight.value_tag` in place, including annotated insights and
all server types. IDs, timestamps, annotations and votes are preserved.
It does not delete duplicate records: multiple predictions or insights can
legitimately refer to the same brand. Grouped counts use the canonical tag.

API filters accept both legacy and canonical brand tags for predictions,
insights and questions. Responses always expose the stored canonical tag
after migration, even when a request uses a legacy tag. Clients comparing
tags in the frontend must use the canonical form. Other types retain exact
matching. This does not change product `brands` filters, logo annotation
identifiers or taxonomy synonym resolution.

## Deployment, after design approval

Back up the affected tables and measure the migration on a staging copy.
Pause prediction and insight writers, deploy the revised code, run the
normal migration command, and resume writers only after it completes.
Readers should switch with the migration: canonical queries assume existing
rows have been migrated. Old writers must not run after migration.

The migration is idempotent but may update many rows and hold locks until
the migration transaction commits. Plan the maintenance window using the
staging measurement. Its rollback deliberately preserves the canonical
tags; restoring original spellings requires the backup because both forms
may have existed before the migration.

Run `make integration-tests` to exercise the PostgreSQL migration, stored
values, API responses, counts, import deduplication and vote preservation.
