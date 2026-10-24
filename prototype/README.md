# TraceyDB functional prototype

A local web interface backed by the project's PostgreSQL database. The backend uses FastAPI, Uvicorn and Psycopg 3, with Python 3.10+ and PostgreSQL. The existing HTML/CSS/JavaScript interface needs no front-end build step. PostgreSQL's `psql` client is used for database setup and integration tests only.

## Start

1. Install the database using `database/README.md`, or use the existing TraceyDB on port 55432.
2. Run `psql -h 127.0.0.1 -p 55432 -U supplytrace_test -d TraceyDB -f prototype/setup_access.sql` as the database setup user. On Windows, use the full path to psql if necessary. This creates the restricted `tracey_web` login and grants it the existing `supplytrace_app` role.
3. Install dependencies with `python -m pip install -r prototype/requirements-lock.txt`. Then run `python prototype/server.py`, or `./prototype/start.ps1` in PowerShell. Installed dependencies are excluded from the repository; install them using the lock file.
4. Open http://127.0.0.1:8765 in your browser. Leave the server running while using the prototype; Ctrl+C stops it.

Defaults: `PGHOST=127.0.0.1`, `PGPORT=55432`, `PGDATABASE=TraceyDB`, `PGUSER=tracey_web`. Override these environment variables for another local installation. `TRACEY_PORT` selects the web port. Psycopg uses PostgreSQL environment variables directly; `PSQL` is only relevant to database command-line tooling. Use `.pgpass` or another PostgreSQL-supported credential mechanism when password authentication is configured. The existing project cluster uses loopback trust authentication. The application itself contains no password.

## Workflows

- **Overview:** live counts, eligible stock and order status totals.
- **Product catalogue:** search models, chip, storage, colour and SKU; compare eligible stock.
- **Inventory:** search by product, city or manufacturing batch; place a batch on quality hold after confirmation.
- **Orders and dispatch:** create an order with up to 20 lines, optionally allocate immediately, inspect allocations and dispatch all or part of each remaining allocation.
- **Component tracing:** enter a component lot ID to see its supplier, manufacturing batches, warehouse stock and recipients. Lot 11 is the seeded recall example.

The create-and-allocate option calls both existing database functions in one transaction. If allocation fails, the new order and every reservation are rolled back. Every write uses the existing controlled functions as `supplytrace_app`; the web login has no direct table-write privilege. The service permits at most two concurrent database connections, opened through Psycopg and closed after each transaction. User values are bound as SQL parameters. FastAPI validates request bodies with strict positive integer quantities and rejects unknown fields. Psycopg commits successful transactions and rolls back failed operations, including a failure on a later order line. Mutations require a per-server CSRF token and a permitted loopback host/origin.

This is a single-user, loopback-only coursework application. It has no user-account authentication and must not be exposed to the internet. Requests make real changes to the selected database. Holds cannot be released through this prototype. A database timeout or business-rule rejection is shown to the user; failed transactions are rolled back. PostgreSQL identity sequences can have gaps after rollback.

## Suggested three-minute demonstration

1. **0:00–0:25:** show Overview and explain the supply-chain problem and synthetic data.
2. **0:25–0:50:** search the catalogue for iPhone 17 Pro and inspect eligible warehouse stock.
3. **0:50–1:30:** create a two-unit order for SKU `IP17P-256-DB` with allocation enabled, then dispatch one unit. Show the partial-dispatch status and recorded destination; dispatch the remaining unit.
4. **1:30–2:05:** create an order with one available line and a second line for `MBA13M4-512-MN`, which has no stock in the original seed. Show the insufficient-stock error and that no new order was saved. Use the original seed or check stock first if the database has been changed.
5. **2:05–2:45:** trace component lot 11, explain the affected batches, remaining stock and shipped recipients. Optionally place an affected batch on hold at the end; this changes subsequent stock availability.
6. **2:45–3:00:** explain that PostgreSQL enforces stock, allocation and shipment consistency, including rollback and concurrent allocation safeguards.

Use a freshly seeded disposable database for repeatable recording. The original seed contains 69,533 rows; new orders and shipments naturally change its row counts.

## Verification

Run `python prototype/tests/integration_test.py` on the existing Windows PostgreSQL 18 installation. It uses the local setup account and port 55432, creates `TraceyDB_prototype_verify`, loads a fresh seed, starts a separate server on port 8766, runs 22 API checks, and removes the temporary database. It fails without overwriting an existing database of that name. The setup account requires database and role creation privileges. Results are written to `prototype/evidence/api_tests.json`. Generated test results are excluded from the repository.

## API documentation

Open http://127.0.0.1:8765/docs for the interactive OpenAPI documentation, or `/openapi.json` for its schema. The Swagger UI and ReDoc pages load their standard documentation assets from a CDN, so those pages need an internet connection. The operational interface works locally. POST requests require the `X-Tracey-Token` header using the token returned by `GET /api/session`; the web interface handles this automatically. In Swagger UI, execute `/api/session`, copy its token, and paste it into the Authorize dialogue before trying a POST operation. The backend uses the same PostgreSQL functions and restricted role as the original prototype.

## Table sorting

Click a column heading in Product catalogue, Inventory or Orders & dispatch to sort ascending; click it again for descending. Chip and storage, and product and batch, have separate controls. Sorting applies in PostgreSQL before pagination and combines with the search filter. Null values appear last; a unique identifier provides stable ordering for ties. Run `python prototype/tests/sorting_test.py` against the running local app for read-only sorting checks.

Refresh resets the table to its default sort and page 1 while retaining the current search filter.

## Generated verification results

Tests write their results to `prototype/evidence/`. Generated screenshots, test outputs and coursework reports are excluded from this source repository.
