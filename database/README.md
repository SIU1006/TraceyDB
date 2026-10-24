# TraceyDB PostgreSQL implementation

The dataset contains **69,533 rows across fifteen tables**, with 1,453 Apple product configurations across 146 shared product models. Product names, selected components, storage options and colours come from public specifications. Organisations and operational records are synthetic. See [CATALOGUE_SOURCES.md](CATALOGUE_SOURCES.md) for sources, assumptions, attribution and the independence notice.

## Requirements and reproduction

PostgreSQL 18, `psql`, and Python 3 (standard library only for the test runner). Use a fresh database owned by your setup user. The schema script intentionally fails if `supplytrace` already exists; it never drops existing data.

Run the commands from the project root (the folder containing `database/`). The checked-in CSV files can be regenerated with `python database/generate_data.py`; generation is deterministic. `data_manifest.json` lists every table count.

The initial load deliberately runs before the deferred audit triggers are installed. Primary keys, foreign keys and CHECK constraints remain active. The subsequent whole-database audit validates the completed load. Do not use this fresh-install sequence to append data to an existing database.

Set `PGHOST`, `PGPORT`, `PGUSER` and `PGDATABASE` for your own database. For this project, set `PGDATABASE=TraceyDB` (case-sensitive). The internal `supplytrace` schema and application role names remain unchanged. Use `.pgpass` or `PGPASSFILE` for authentication rather than storing a password in these files.

```text
createdb TraceyDB
psql -X -v ON_ERROR_STOP=1 -f database/01_schema.sql
psql -X -v ON_ERROR_STOP=1 -f database/03_seed.sql
psql -X -v ON_ERROR_STOP=1 -f database/02_operations.sql
psql -X -v ON_ERROR_STOP=1 -c "SELECT supplytrace.assert_consistent()"
psql -X -v ON_ERROR_STOP=1 -f database/05_access.sql
psql -X -v ON_ERROR_STOP=1 -f database/07_catalogue_view.sql
psql -X -v ON_ERROR_STOP=1 -f database/04_queries.sql
psql -X -v ON_ERROR_STOP=1 -f database/06_row_counts.sql
psql -X -v ON_ERROR_STOP=1 -f database/08_component_queries.sql
python database/tests/check_component_data.py
python database/tests/check_component_quantities.py
python database/tests/run_tests.py
```

The access script requires CREATEROLE privileges. `supplytrace_app` is a NOLOGIN role with read access and permission to call four controlled write functions. Assign it to your application's login; do not connect the application as the database owner. Direct writes are reserved for trusted setup/administration. The test runner requires the setup account (including SET ROLE permission), so use it only on a disposable seeded database. Set `PSQL` to an absolute psql executable if it is not on PATH.

## Operations

```sql
BEGIN;
SET LOCAL ROLE supplytrace_app;
SELECT supplytrace.create_order(2001,1,ARRAY['IP17P-256-DB'],ARRAY[2]);
SELECT supplytrace.allocate_order(2001);
COMMIT;
-- Use an allocation_id returned by a query of supplytrace.stock_allocation:
-- SELECT supplytrace.dispatch_allocation(<allocation_id>, 1);
-- SELECT supplytrace.hold_batch(101);
```

Each API call is atomic under autocommit, or can form part of an explicit multi-step transaction. Do not catch a failed transaction and commit unrelated earlier writes; roll back the transaction. The test runner uses rolled-back transactions for ordinary tests and restores the two committed concurrency fixtures afterwards. Identity values may have gaps after rollback; this is expected and has no business meaning.

## Design and limits

- Fifteen tables correspond to Section 3; camelCase report attributes map to snake_case SQL names.
- Application writes use one transaction-level advisory lock `(9120,1)` and READ COMMITTED isolation. This serialises allocation, dispatch, order creation and holds, including simultaneous quality changes. Inventory and order rows are also locked where relevant.
- Deferred constraint triggers audit final transaction state. They scan the complete demonstration database, so repeated audits are not optimised for production throughput. Supporting indexes cover the audit joins; passing the tests at this size is not a load benchmark.
- The application role cannot bypass the functions. Privileged direct SQL is for maintenance, not concurrent application traffic; an administrator must follow the same writer-lock protocol.
- The dispatch function creates one shipment line per call. The schema permits multi-line shipments, but there is no batch-dispatch API in this scope.
- A local web prototype is provided in `../prototype`; see its README for launch instructions and the demonstration workflow. Deployment authentication, returns, cancellations, reservation release, transfers and serial-number tracking are outside the implemented scope.
- The local test cluster uses trust authentication only on loopback and can be stopped when no longer needed. Use password authentication and appropriate secrets management for deployment.

## Generated verification results

Test scripts write their results to `database/evidence/`. Generated logs and historical verification bundles are excluded from this source repository. Run the verification commands above against a disposable seeded database to produce fresh results.

## Expanded catalogue

`catalogue.json` records the reviewed model, storage, finish, chip, year and Apple source URL. The catalogue spans iPhone X onwards, iPad from 2017 onwards, Apple-silicon Macs, AirPods and Apple Watch, plus the existing Vision Pro entries. It is a historical teaching catalogue; discontinued entries do not imply current retail availability. Chip, storage and colour are configuration attributes. Model names retain essential sizes; release year is a separate model attribute. RAM, band choices, regional radio versions and every CPU/GPU core-count option are outside this catalogue.

The current schema and CSV files already include the catalogue simplification and component expansion. Historical migration scripts are no longer distributed. Use the fresh-install sequence above; the script numbers are identifiers, not execution order.

## Browsing the simplified catalogue

`product_model` has 146 models with model_id, model_name, product_family and release_year. Essential sizes remain in the model name. `product_configuration` has 1,453 SKUs with model_id, chip, storage_capacity_gb and colour. A null-aware unique constraint prevents equivalent configurations. `product_catalogue` joins both tables and generates display_name.

```sql
SELECT model_name, release_year, chip, storage_capacity_gb, colour, sku
FROM supplytrace.product_catalogue
WHERE model_name = 'MacBook Pro 14-inch'
ORDER BY release_year, chip, storage_capacity_gb;
```

Storage uses advertised decimal GB (1TB = 1000GB). NULL means inapplicable or unverified. Release month, connectivity, material and port variants are outside the simplified scope. `catalogue_sku_aliases.csv` maps all 1,512 original catalogue SKUs to their retained identifiers; 59 equivalent configurations were consolidated. Source descriptions remain in catalogue.json for provenance and reproducibility. All operational rows and quantities are retained.

The current schema excludes generation. Original source descriptions remain available in catalogue.json.

## Expanded components

The catalogue contains 143 component types and 3,284 received component lots. All 2,111 existing manufacturing batches have 9–11 recorded inputs, giving 23,189 usage rows. Adding these records increases the total to 69,533 while preserving existing orders, inventory and shipments. The family-level assemblies are synthetic specifications; their naming does not imply physical interchangeability across model revisions. Supplier links and one-assembly-or-set-per-device quantities are simulated. Watch and AirPods parts are registered, but no manufacturing stock is asserted for those catalogue-only products.

Run `python database/tests/check_component_data.py` for coverage validation. `08_component_queries.sql` provides component browsing, batch input and supplier examples.

## Script roles

Install in this order: `01_schema.sql`, `03_seed.sql`, `02_operations.sql`, `05_access.sql`, `07_catalogue_view.sql`. Run the consistency assertion after installing the operations, as shown above. The seed must precede the operations so that the whole-database audit triggers are installed after the bulk load.

`04_queries.sql`, `06_row_counts.sql` and `08_component_queries.sql` are read-only demonstration and verification scripts. The Python entry point is `generate_data.py`; it imports `expand_catalogue.py`, `normalise_catalogue.py` and `expand_components.py`. Keep all four together. The supplied CSV files allow installation without regenerating the data.

Component quantities count individual parts or complete named assemblies, sets or pairs. For example, a quantity of 10 for an audio driver pair means 10 pairs. This fixed counting convention is defined here rather than stored in a per-component measurement column. Synthetic-data provenance applies to the dataset as a whole and is omitted from individual component names.

Component receipt and consumption quantities are positive whole counts, capped at 99,999,999,999 to preserve the former quantity range. Unconstrained PostgreSQL `numeric` storage and explicit whole-number CHECK constraints reject fractional inputs before any scale rounding. The checks also exclude non-finite values. Run `python database/tests/check_component_quantities.py` with the same PostgreSQL environment variables as the main test runner; all writes roll back. Results are saved in `evidence/component_quantity_checks.json`.
