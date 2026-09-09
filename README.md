# TallyPrime to MySQL Integration

A FastAPI and React dashboard that extracts ledger and voucher data from TallyPrime over XML/HTTP, transforms it, and stores it in MySQL. The React application communicates only with FastAPI. It never connects directly to TallyPrime or MySQL and contains no database or Tally credentials.

## 1. Project Overview

The system supports:

- TallyPrime connection testing
- MySQL connection testing
- Ledger synchronization
- Date-window voucher synchronization
- Full synchronization in dependency order
- Checkpoint-based incremental synchronization
- Idempotent ledger and voucher upserts
- Voucher-entry relationships through MySQL foreign keys
- Synchronization history and checkpoint state
- A browser dashboard with live API data

The root-level scripts such as `parse_vouchers.py` and `sync_vouchers.py` are retained as development/prototyping history. The application uses the reusable code under `backend/`.

## 2. Architecture

```text
React + Vite dashboard
        |
        | HTTP/JSON through /api
        v
FastAPI backend
        |
        +--> Tally transport and XML parser --> TallyPrime HTTP server
        |
        +--> repositories and transactions --> MySQL
        |
        +--> sync_log and sync_state
```

Backend layers:

- `backend/api/`: FastAPI routes and response schemas
- `backend/services/`: Tally transport, parsing, orchestration, and business logic
- `backend/database/`: MySQL connection and repository operations
- `backend/utils/`: date conversion and XML sanitization
- `frontend/src/`: React dashboard and API client

## 3. Technologies

- Python 3.13-compatible backend code
- FastAPI
- Uvicorn
- MySQL 8.0
- `mysql-connector-python`
- `requests`
- `python-dotenv`
- React 19
- Vite
- `lucide-react`
- Oxlint

## 4. Tally Configuration

Configure TallyPrime as an HTTP server on the local machine. The default project configuration expects:

- URL: `http://localhost:9000`
- Company: `Tally MySQL Integration Demo`

Tally must be running and the configured company must be open. The backend sends:

- A ledger collection request for ledger synchronization and connection testing
- A Day Book request with `SVFROMDATE` and `SVTODATE` for voucher synchronization

The backend sanitizes invalid XML control characters before parsing Tally responses and rejects unsuccessful Tally statuses.

## 5. MySQL Configuration

Create the database and provide the existing project schema containing these logical tables:

- `ledgers`
- `vouchers`
- `voucher_entries`
- `sync_log`
- `sync_state`

The application expects the voucher identity column `vouchers.tally_voucher_key` and a unique constraint on it. Ledger names are the current ledger business key.

Do not create a schema by guessing column types. Use the existing project/database schema for the deployment.

## 6. Environment Setup

Copy the example file:

```text
.env.example -> .env
```

Set the real local values in `.env`:

```dotenv
TALLY_URL=http://localhost:9000
TALLY_COMPANY=Tally MySQL Integration Demo
TALLY_TIMEOUT_SECONDS=30

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_local_password
MYSQL_DATABASE=tally_integration
```

`MYSQL_USER`, `MYSQL_PASSWORD`, and `MYSQL_DATABASE` are required by the backend. `.env` is ignored by Git. Never place credentials in React source files or commit them to the repository.

Install Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

Install frontend dependencies:

```powershell
cd frontend
npm install
```

## 7. Backend Setup

From the repository root, start FastAPI:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Useful backend URLs:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Health: `http://127.0.0.1:8000/api/health`

If port 8000 is already occupied, stop the old Uvicorn process before restarting. The frontend proxy defaults to port 8000.

## 8. Frontend Setup

Start the dashboard from the `frontend/` directory:

```powershell
npm run dev
```

The normal development URL is:

```text
http://127.0.0.1:5173/
```

The Vite development proxy forwards `/api` requests to FastAPI. The target defaults to port 8000 and can be changed for testing:

```powershell
$env:VITE_API_PROXY_TARGET="http://127.0.0.1:8001"
npm run dev -- --host 127.0.0.1 --port 5174
```

The frontend does not store or read MySQL/Tally credentials.

## 9. Running the Application

1. Start MySQL.
2. Start TallyPrime and open the configured company.
3. Confirm `.env` values.
4. Start FastAPI.
5. Start the Vite frontend.
6. Open the dashboard.
7. Test the TallyPrime and MySQL connections.
8. Run a full sync for the initial load.
9. Use incremental sync for routine updates.

The dashboard displays live records returned by FastAPI, including ledgers, vouchers, voucher entries, sync history, and the latest synchronization result.

## 10. Synchronization Workflow

### Ledger synchronization

`POST /api/sync/ledgers`:

1. Requests the Tally ledger collection.
2. Sanitizes and parses the XML.
3. Upserts ledgers by name.
4. Commits the transaction.
5. Writes a synchronization log.

### Voucher synchronization

`POST /api/sync/vouchers` receives `from_date` and `to_date`:

1. Requests the Tally Day Book for that date range.
2. Parses voucher headers and repeated ledger entries.
3. Finds the destination voucher by `tally_voucher_key`.
4. Inserts a new voucher or updates an existing voucher.
5. Deletes and recreates that voucher's entries inside the same transaction.
6. Fails explicitly if a referenced ledger does not exist.
7. Saves the voucher checkpoint only after successful data work.
8. Writes a synchronization log.

### Full synchronization

`POST /api/sync/full` runs ledgers first and then vouchers for the configured full date window. Voucher entries are persisted as part of voucher synchronization.

### Incremental synchronization

`POST /api/sync/incremental` reads the `VOUCHER` checkpoint from `sync_state` and rereads from that date through today. This is a date-window reread with idempotent upserts. It does not detect every source-side change automatically and is not a change-data-capture system.

Repeated synchronization updates existing records instead of creating duplicate voucher keys.

## 11. Database Relationships

```text
ledgers (1) -------- (many) voucher_entries (many) -------- (1) vouchers
```

- `voucher_entries.voucher_id` references `vouchers.id`
- `voucher_entries.ledger_id` references `ledgers.id`
- `vouchers.tally_voucher_key` identifies a Tally voucher for synchronization
- `ledgers.name` identifies a ledger in the current demo implementation
- Voucher amounts are handled with `Decimal` in Python and should use a fixed-point MySQL type such as `DECIMAL(18,2)`

## 12. API Endpoints

### System and connections

| Method | Endpoint          | Purpose                                             |
| ------ | ----------------- | --------------------------------------------------- |
| `GET`  | `/api/health`     | Process health check                                |
| `POST` | `/api/tally/test` | Test Tally connectivity and parse a ledger response |
| `POST` | `/api/mysql/test` | Test MySQL connectivity                             |

### Data

| Method | Endpoint               | Purpose                                  |
| ------ | ---------------------- | ---------------------------------------- |
| `GET`  | `/api/ledgers`         | Return synchronized ledgers              |
| `GET`  | `/api/vouchers`        | Return synchronized vouchers             |
| `GET`  | `/api/voucher-entries` | Return voucher entries with ledger names |

### Synchronization

| Method | Endpoint                | Purpose                                             |
| ------ | ----------------------- | --------------------------------------------------- |
| `POST` | `/api/sync/ledgers`     | Synchronize ledgers                                 |
| `POST` | `/api/sync/vouchers`    | Synchronize a supplied date window                  |
| `POST` | `/api/sync/full`        | Run ledgers followed by vouchers                    |
| `POST` | `/api/sync/incremental` | Run from the saved voucher checkpoint through today |
| `GET`  | `/api/sync/history`     | Return recent synchronization logs                  |
| `GET`  | `/api/sync/state`       | Return synchronization checkpoints                  |

Voucher request example:

```json
{
  "from_date": "2026-09-01",
  "to_date": "2026-09-09"
}
```

## 13. Testing

Backend syntax/build check:

```powershell
python -m compileall -q backend
```

Frontend lint and production build:

```powershell
cd frontend
npm run lint
npm run build
```

Existing integration scripts:

```powershell
python test_tally.py
python test_mysql.py
python parse_vouchers.py
python sync_vouchers.py
```

The verified local integration flow tested:

- TallyPrime and MySQL connection endpoints
- Real ledger and voucher synchronization
- Full and incremental synchronization
- Duplicate voucher prevention
- Voucher-entry foreign-key relationships
- Sync history and checkpoint persistence
- Invalid date errors
- Transaction rollback after an induced missing-ledger failure
- React rendering of live API data and synchronization controls

A new-voucher insertion test requires a newly created Tally transaction in the configured date window. Existing-voucher update behavior and duplicate prevention have been verified against the current local data.

## 14. Known Limitations

- Incremental synchronization is date-window based, not source-side change tracking.
- The current checkpoint is maintained for vouchers; ledger synchronization is full-list based.
- Full synchronization uses a fixed start date in the current route implementation.
- The current API has no authentication, authorization, rate limiting, or audit-user identity.
- API list endpoints return all records and do not yet provide pagination or filtering.
- The dashboard system-status label is a simple UI indicator; connection tests provide the authoritative result.
- Sync logs are written per ledger/voucher operation; aggregate full/incremental summaries are returned by the API but are not currently a separate log type.
- The repository retains prototype scripts that duplicate some older extraction logic. They are not the primary web application path.
- Automated test coverage is limited; live integration checks require running TallyPrime and MySQL.

## 15. Production Considerations

Before production deployment:

- Put FastAPI behind a production ASGI process manager and reverse proxy.
- Use HTTPS and restrict network access to the API and Tally endpoints.
- Add authentication and role-based authorization to synchronization routes.
- Store secrets in a managed secret store rather than a local `.env` file.
- Use a least-privilege MySQL account instead of `root`.
- Add database migrations and validate the production schema explicitly.
- Add structured logging, monitoring, alerting, and request correlation IDs.
- Add retry/backoff policy for transient Tally and MySQL failures.
- Add concurrency protection so overlapping sync runs cannot race each other.
- Add pagination and server-side filtering for large data sets.
- Add automated unit, integration, rollback, and browser tests in CI.
- Review Tally HTTP exposure and bind it only to trusted interfaces.
- Define retention and access policies for synchronization history and error messages.
