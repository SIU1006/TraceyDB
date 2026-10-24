# TraceyDB

A PostgreSQL supply-chain database and local web prototype for product inventory, orders, allocation, dispatch and component traceability. Built for COMP9120 Database Management at the University of Sydney.

The reproducible seed contains 69,533 rows across 15 tables, including 146 product models and 1,453 product configurations. Operational records and organisations are synthetic; product references and assumptions are documented in [database/CATALOGUE_SOURCES.md](database/CATALOGUE_SOURCES.md).

## Contents

- [database/](database/): schema, controlled SQL operations, seed CSVs, catalogue provenance, deterministic data generators and verification scripts.
- [prototype/](prototype/): FastAPI backend, HTML/CSS/JavaScript interface, dependency lock file and API tests.

## Run locally

Requires PostgreSQL 18 with its command-line tools and Python 3.10 or later. Run commands from the repository root.

1. Follow [database/README.md](database/README.md) to create and seed a fresh database. The installation order is `01_schema.sql`, `03_seed.sql`, `02_operations.sql`, the consistency assertion, `05_access.sql`, then `07_catalogue_view.sql`.
2. Set the PostgreSQL connection variables for your installation. The prototype defaults to `PGHOST=127.0.0.1`, `PGPORT=55432`, `PGDATABASE=TraceyDB` and `PGUSER=tracey_web`. Use a PostgreSQL-supported credential mechanism such as `.pgpass` when required.
3. Run `prototype/setup_access.sql` as your database setup user to create the restricted application login.
4. Install dependencies: `python -m pip install -r prototype/requirements-lock.txt`.
5. Start the app: `python prototype/server.py`.
6. Open <http://127.0.0.1:8765>.

See [prototype/README.md](prototype/README.md) for the workflows, demonstration and API documentation. The prototype is a single-user coursework app intended for loopback access and has no user-account authentication.

## Verification

The database README documents the database checks. `python database/tests/check_component_data.py` validates the seed coverage without a running database. Other SQL and integration checks require a disposable, seeded PostgreSQL database. The prototype integration test currently targets the documented local Windows PostgreSQL 18 installation; review its connection settings before running it elsewhere.

Test outputs are generated under ignored `evidence/` directories. Reports, submission documents, screenshots, ZIP archives, local dependencies and temporary files are excluded from this repository.
