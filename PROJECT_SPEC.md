# TallyPrime → MySQL Integration System
## Project Specification for Codex

---

# 1. PROJECT GOAL

Build a complete, user-friendly TallyPrime to MySQL data integration system.

The system should allow an operator to synchronize data from TallyPrime into MySQL through a web-based UI instead of manually running Python scripts or SQL commands.

The final architecture should be:

    TallyPrime
         |
         | XML over HTTP
         v
    Python FastAPI Backend
         |
         | Parse / Validate / Transform / Sync
         v
       MySQL
         ^
         |
    React Frontend
         |
       Operator

The frontend must NOT communicate directly with Tally or MySQL.

The React frontend communicates only with the FastAPI backend.

The FastAPI backend contains the integration logic.

---

# 2. IMPORTANT CONTEXT

This project is being developed as a technical/HR demonstration project.

The goal is not only to make the application work, but also to demonstrate understanding of:

- Tally integration
- XML over HTTP
- Python integration
- XML parsing
- data transformation
- relational database design
- primary keys
- foreign keys
- voucher/ledger relationships
- INSERT/UPDATE synchronization
- idempotency
- incremental synchronization
- transaction handling
- synchronization logging
- error handling
- API architecture
- frontend/backend separation

The implementation should therefore be clean and understandable.

Do not over-engineer the application unnecessarily.

---

# 3. CURRENT ENVIRONMENT

Operating System:

Windows

Tally:

TallyPrime 7.1

Tally mode:

Educational Mode

Tally company:

Tally MySQL Integration Demo

Tally HTTP server:

localhost:9000

MySQL:

MySQL Server 8.0

MySQL database:

tally_integration

MySQL username:

root

Do NOT hardcode the MySQL password into source code.

Use environment variables.

Example:

    MYSQL_HOST=localhost
    MYSQL_PORT=3306
    MYSQL_USER=root
    MYSQL_PASSWORD=<password>
    MYSQL_DATABASE=tally_integration

Use a `.env` file locally.

DO NOT commit `.env` to Git.

Create `.env.example`.

---

# 4. EXISTING PROJECT

There are already Python scripts that were developed and tested.

Existing files may include:

    test_tally.py
    test_mysql.py
    test_vouchers.py
    parse_vouchers.py
    tally_to_mysql.py
    sync_ledgers.py
    sync_voucher_to_mysql.py
    sync_vouchers.py

DO NOT immediately delete these files.

They represent the development/prototyping history.

Inspect them first.

Reuse their working logic where appropriate.

The goal is to refactor working logic into reusable backend services rather than rewriting everything blindly.

---

# 5. EXISTING TALLY CONNECTION

TallyPrime is configured as an HTTP server.

Port:

    9000

Python has already successfully tested:

    POST http://localhost:9000

and received:

    HTTP Status: 200

    <TallyPrime Server is Running></RESPONSE>

This proves that the Python application can communicate with Tally.

The backend must have a Tally connection service responsible for:

- sending requests
- receiving responses
- timeout handling
- connection errors
- response validation
- XML sanitization where necessary

Do not expose Tally directly to the React frontend.

---

# 6. TALLY XML COMMUNICATION

The current project uses XML over HTTP.

A representative Day Book request is:

    <ENVELOPE>
        <HEADER>
            <VERSION>1</VERSION>
            <TALLYREQUEST>EXPORT</TALLYREQUEST>
            <TYPE>DATA</TYPE>
            <ID>DayBook</ID>
        </HEADER>
        <BODY>
            <DESC>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>Tally MySQL Integration Demo</SVCURRENTCOMPANY>
                    <SVFROMDATE TYPE="Date">01-Sep-2026</SVFROMDATE>
                    <SVTODATE TYPE="Date">30-Sep-2026</SVTODATE>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                </STATICVARIABLES>
            </DESC>
        </BODY>
    </ENVELOPE>

The backend should construct requests programmatically.

Do not scatter XML strings throughout the codebase.

Create a Tally request/service layer.

---

# 7. TALLY LEDGER DATA

The current project has successfully extracted ledgers from Tally.

Example ledger names include:

    ABC Technologies
    Cash
    Computer World
    Electricity Expense
    Hardware Distributors
    HDFC Bank
    Mysore Computers
    Profit & Loss A/c
    Purchase
    Rent Expense
    Salary Expense
    Sales
    Tech Supplier India
    XYZ Solutions

The existing ledger extraction uses:

    TYPE = COLLECTION

    ID = List of Ledgers

and requests fields such as:

    Name
    Parent

The backend should support ledger synchronization.

---

# 8. TALLY VOUCHER DATA

The current project has successfully extracted voucher information.

A representative voucher contains fields such as:

    DATE
    VOUCHERTYPENAME
    VOUCHERNUMBER
    NARRATION
    MASTERID
    ALTERID
    VOUCHERKEY

It also contains repeated ledger entries:

    ALLLEDGERENTRIES.LIST

Each ledger entry may contain:

    LEDGERNAME
    AMOUNT

Example conceptual voucher:

    Payment
    Date: 2026-09-02
    Number: 1
    Narration: Demo payment for Tally MySQL integration

    Ledger Entry:
        Rent Expense
        -1000.00

    Ledger Entry:
        Cash
        1000.00

Important:

One voucher can contain multiple ledger entries.

Therefore voucher and voucher entries must NOT be stored as one flat row.

---

# 9. XML SANITIZATION

Tally XML may contain invalid XML character references such as:

    &#4;

This previously caused:

    xml.etree.ElementTree.ParseError:
    reference to invalid character number

The existing project has a sanitization step before parsing.

Preserve this behavior.

Create a reusable XML sanitization utility.

The flow should be:

    Tally Response
          |
          v
    Sanitize XML
          |
          v
    XML Parser
          |
          v
    Structured Python objects

If parsing fails, return a meaningful error instead of crashing the entire application.

---

# 10. DATABASE DESIGN

Existing database:

    tally_integration

The system currently uses these logical tables:

    ledgers
    vouchers
    voucher_entries
    sync_log
    sync_state

Do not redesign the schema unnecessarily unless there is a clear technical reason.

---

# 11. LEDGERS TABLE

Current logical structure:

    ledgers

Columns:

    id
    name
    parent
    created_at
    updated_at

`id` is the MySQL internal primary key.

`name` identifies the ledger within the current demo.

There is a unique constraint on ledger name in the current implementation.

The backend should use idempotent synchronization.

If a ledger already exists:

    UPDATE

If it does not exist:

    INSERT

Do not create duplicate ledger records during repeated synchronization.

---

# 12. VOUCHERS TABLE

Current logical structure:

    vouchers

Columns:

    id
    tally_master_id
    tally_alter_id
    tally_voucher_key
    voucher_date
    voucher_type
    voucher_number
    narration
    created_at
    updated_at

Important:

`tally_voucher_key` is the current synchronization identity used by the demo.

It has a unique constraint.

The MySQL `id` is a destination-side internal identifier.

Do not confuse MySQL primary key with Tally source identifiers.

---

# 13. VOUCHER_ENTRIES TABLE

Current logical structure:

    voucher_entries

Columns:

    id
    voucher_id
    ledger_id
    amount

Relationships:

    vouchers 1 ---- N voucher_entries

    ledgers  1 ---- N voucher_entries

Foreign keys:

    voucher_entries.voucher_id
        ->
    vouchers.id

and:

    voucher_entries.ledger_id
        ->
    ledgers.id

This represents the relational structure of Tally voucher data.

---

# 14. WHY THE SCHEMA LOOKS LIKE THIS

Do not create tables by guessing.

The schema is derived using this process:

    Tally XML
        |
        v
    Inspect source fields
        |
        v
    Identify business entities
        |
        v
    Identify repeated/nested structures
        |
        v
    Map entities to relational tables
        |
        v
    Select data types
        |
        v
    Define primary/foreign keys
        |
        v
    Add source identifiers for synchronization

For example:

DATE:

    Tally DATE
        ->
    voucher_date DATE

VOUCHERTYPENAME:

    ->
    voucher_type VARCHAR

VOUCHERNUMBER:

    ->
    voucher_number VARCHAR

NARRATION:

    ->
    narration TEXT

MASTERID:

    ->
    tally_master_id BIGINT

ALTERID:

    ->
    tally_alter_id BIGINT

VOUCHERKEY:

    ->
    tally_voucher_key VARCHAR

Repeated:

    ALLLEDGERENTRIES.LIST

becomes:

    voucher_entries

Do not flatten repeated ledger entries into voucher columns.

---

# 15. MONEY HANDLING

Do NOT use Python float for financial values if avoidable.

Use:

    decimal.Decimal

and MySQL:

    DECIMAL(18,2)

Example:

    -1000.00

must remain exactly:

    -1000.00

Do not introduce floating-point rounding errors.

---

# 16. DATE TRANSFORMATION

Tally may return:

    20260902

The application should transform it into a Python date / MySQL-compatible date:

    2026-09-02

Date parsing must be centralized in the transformation layer.

Invalid dates must be rejected with a useful error.

---

# 17. LEDGER NAME → LEDGER ID

Tally voucher entries may contain:

    LEDGERNAME = "Rent Expense"

The database relationship requires:

    ledger_id

Therefore the synchronization process should:

1. Find the ledger by source/business identifier.
2. Obtain the MySQL ledger ID.
3. Insert the voucher entry using that ledger ID.

If the ledger does not exist:

- handle the situation explicitly
- either synchronize ledgers first or report the missing ledger
- do not create a broken foreign key
- do not silently ignore the entry

---

# 18. INITIAL SYNC

The application must support an initial/full synchronization.

Purpose:

Load existing Tally data into a new/empty MySQL database.

Conceptually:

    Tally
      |
      v
    Extract ledgers
      |
      v
    Store ledgers
      |
      v
    Extract vouchers
      |
      v
    Store vouchers
      |
      v
    Store voucher entries

The initial sync should be safe to repeat.

Repeated execution must not create duplicates.

---

# 19. INCREMENTAL SYNCHRONIZATION

The project should support incremental synchronization.

The current implementation is:

    date-window based
    +
    idempotent upsert

Do NOT claim that it extracts only perfectly changed records unless the implementation actually does so.

The system may re-read a date window, but existing records should be updated rather than duplicated.

Example:

First sync:

    Extracted: 1
    Inserted: 1
    Updated: 0
    Failed: 0

Second sync:

    Extracted: 1
    Inserted: 0
    Updated: 1
    Failed: 0

No duplicate should be created.

---

# 20. SYNC_STATE

Current logical table:

    sync_state

Purpose:

Store the latest synchronization checkpoint/state.

Fields include:

    entity_type
    last_sync_date
    last_sync_time
    updated_at

Use it to determine the synchronization window/state.

Do not advance the checkpoint if the synchronization operation fails.

---

# 21. SYNC_LOG

Current logical table:

    sync_log

Fields include:

    id
    sync_type
    started_at
    completed_at
    records_extracted
    records_inserted
    records_updated
    records_failed
    status
    error_message

Possible statuses:

    RUNNING
    SUCCESS
    FAILED

Every synchronization should create a log entry.

The UI should be able to display synchronization history.

---

# 22. TRANSACTIONS

Database synchronization must use proper transaction handling.

Important requirement:

If a voucher and its entries are being synchronized, they should be handled consistently.

If a critical database operation fails:

    rollback

Do not leave half-created voucher relationships.

Avoid nested or conflicting transaction handling.

The previous implementation had:

    Transaction already in progress

because transaction management was being mixed incorrectly.

Use one clear transaction strategy.

---

# 23. BACKEND TECHNOLOGY

Use:

    Python
    FastAPI
    MySQL Connector/Python or an appropriate MySQL driver
    Pydantic where useful
    requests/httpx for Tally HTTP communication
    python-dotenv for environment variables

Backend responsibilities:

    Tally communication
    XML sanitization
    XML parsing
    validation
    transformation
    database operations
    synchronization
    transaction management
    logging
    API endpoints

---

# 24. FRONTEND TECHNOLOGY

Use:

    React
    Vite

Do NOT use a frontend framework that adds unnecessary complexity.

The frontend should be a simple professional admin dashboard.

No authentication is required for the initial demo unless specifically requested later.

---

# 25. UI REQUIREMENTS

Create a dashboard with the following sections.

## Connection Status

Display:

    TallyPrime
    MySQL

Each should show:

    Connected
    Disconnected
    Error

Buttons:

    Test Tally Connection
    Test MySQL Connection

---

# 26. DASHBOARD SUMMARY

Display cards such as:

    Total Ledgers
    Total Vouchers
    Total Voucher Entries
    Last Sync
    Last Sync Status

Data should come from backend APIs.

Do not hardcode values.

---

# 27. LEDGER OPERATIONS

Provide:

    Sync Ledgers

Button.

After synchronization display:

    Extracted
    Inserted
    Updated
    Failed

Allow the user to view the ledger list.

---

# 28. VOUCHER OPERATIONS

Provide date fields:

    From Date
    To Date

Button:

    Sync Vouchers

Show result:

    Extracted
    Inserted
    Updated
    Failed

Allow viewing voucher records.

---

# 29. FULL SYNC

Provide a clearly visible:

    Full Synchronization

button.

Before executing, display a confirmation dialog.

The operation should synchronize:

    Ledgers
    Vouchers
    Voucher Entries

The UI should show progress/status.

---

# 30. INCREMENTAL SYNC

Provide:

    Incremental Synchronization

button.

It should use the backend synchronization state.

Show:

    Last Sync
    Current Sync
    Result

---

# 31. SYNC HISTORY

Create a page/section showing:

    Sync Type
    Start Time
    Completion Time
    Extracted
    Inserted
    Updated
    Failed
    Status

Example:

    Voucher Sync
    09-09-2026 06:30
    SUCCESS
    Extracted: 2
    Inserted: 1
    Updated: 1
    Failed: 0

---

# 32. LOG DISPLAY

Show meaningful operational messages.

Examples:

    Tally connection successful
    MySQL connection successful
    Ledger synchronization started
    14 ledgers processed
    Voucher synchronization started
    2 vouchers extracted
    1 voucher inserted
    1 voucher updated
    Synchronization completed successfully

Errors should be understandable.

Do not expose Python stack traces directly to the normal user interface.

---

# 33. API DESIGN

Create clean REST-style endpoints.

Suggested structure:

    GET /api/health

    GET /api/tally/status
    POST /api/tally/test

    GET /api/mysql/status
    POST /api/mysql/test

    POST /api/sync/ledgers

    POST /api/sync/vouchers

    POST /api/sync/full

    POST /api/sync/incremental

    GET /api/ledgers

    GET /api/vouchers

    GET /api/voucher-entries

    GET /api/sync/history

The exact API design may be improved if necessary, but keep it simple.

---

# 34. API RESPONSE FORMAT

Synchronization endpoints should return structured JSON.

Example:

    {
        "status": "success",
        "message": "Voucher synchronization completed",
        "summary": {
            "extracted": 2,
            "inserted": 1,
            "updated": 1,
            "failed": 0
        }
    }

Errors should use appropriate HTTP status codes and useful messages.

---

# 35. PROJECT STRUCTURE

Target structure:

    project-root/
    |
    ├── backend/
    │   ├── main.py
    │   ├── config.py
    │   |
    │   ├── api/
    │   │   ├── connection_routes.py
    │   │   ├── sync_routes.py
    │   │   └── data_routes.py
    │   |
    │   ├── services/
    │   │   ├── tally_service.py
    │   │   ├── mysql_service.py
    │   │   ├── ledger_service.py
    │   │   ├── voucher_service.py
    │   │   ├── sync_service.py
    │   │   └── xml_parser.py
    │   |
    │   ├── database/
    │   │   └── connection.py
    │   |
    │   └── utils/
    │       ├── xml_utils.py
    │       └── date_utils.py
    |
    ├── frontend/
    │   ├── src/
    │   │   ├── components/
    │   │   ├── pages/
    │   │   ├── services/
    │   │   └── App.jsx
    │   └── package.json
    |
    ├── .env
    ├── .env.example
    ├── .gitignore
    ├── README.md
    └── PROJECT_SPEC.md

Existing prototype scripts can remain in their current location initially.

Do not break them unnecessarily.

---

# 36. FRONTEND DESIGN

The UI should look like a professional internal integration/admin tool.

Design principles:

- clean
- simple
- professional
- responsive
- easy to understand
- clear status indicators
- buttons for operations
- tables for data
- confirmation dialogs for major operations
- loading states
- error states
- success notifications

Do not make the UI unnecessarily flashy.

The primary purpose is operational usability.

---

# 37. IMPORTANT UI BEHAVIOR

When the user clicks:

    Test Tally Connection

show:

    Testing...

then:

    Connected ✓

or:

    Connection Failed ✕

Similarly for MySQL.

For synchronization:

    Syncing...

then show final result.

Prevent accidental duplicate clicks while an operation is running.

Disable the button during the active operation.

---

# 38. DO NOT HARD-CODE DATABASE RESULTS

The UI must retrieve actual values from the backend.

For example:

Do NOT write:

    Total Ledgers = 14

Instead call:

    GET /api/ledgers

and calculate/display actual data.

The same applies to vouchers and sync history.

---

# 39. ERROR HANDLING

Handle at least:

- Tally not running
- Tally wrong port
- Tally wrong company
- Tally HTTP timeout
- malformed XML
- invalid Tally XML character references
- MySQL unavailable
- incorrect database credentials
- missing ledger
- duplicate voucher
- database constraint errors
- transaction failure
- unexpected server error

The application should fail gracefully.

---

# 40. SECURITY

Do not expose:

- database passwords
- credentials
- secrets

in frontend source code.

Do not expose MySQL directly to the browser.

Do not expose Tally's HTTP port publicly.

For a real production deployment, communication between systems should use an appropriate private network/VPN/secure gateway architecture.

For this local demo:

    Tally -> localhost:9000
    FastAPI -> localhost:3306
    React -> FastAPI

is sufficient.

---

# 41. MULTI-COMPANY FUTURE CONSIDERATION

The current demo uses one Tally company:

    Tally MySQL Integration Demo

Do not implement full multi-company support unless necessary.

However, keep the architecture extensible.

For production, source identifiers such as voucher keys may need to be scoped by company.

Do not make unsupported claims that the current demo is production-ready for unlimited Tally companies.

---

# 42. TALLY VERSION CONSIDERATION

Do not claim that one integration method is identical for every Tally version.

The current implementation targets TallyPrime XML integration.

Keep Tally communication isolated inside a service/adapter layer so that future support for other formats such as JSON can be added without rewriting the entire application.

---

# 43. DEVELOPMENT APPROACH

IMPORTANT:

Do NOT build the entire project in one huge change.

Work incrementally.

Recommended implementation order:

PHASE 1:
Inspect existing project.

PHASE 2:
Understand and preserve existing working Tally integration.

PHASE 3:
Create/refactor reusable Python services.

PHASE 4:
Create MySQL database service.

PHASE 5:
Create FastAPI backend.

PHASE 6:
Implement connection APIs.

PHASE 7:
Implement ledger synchronization API.

PHASE 8:
Implement voucher parsing and synchronization API.

PHASE 9:
Implement sync logging/state.

PHASE 10:
Implement full/incremental synchronization.

PHASE 11:
Create React application.

PHASE 12:
Create dashboard.

PHASE 13:
Connect frontend to backend.

PHASE 14:
Test complete end-to-end flow.

PHASE 15:
Improve error handling and UI.

---

# 44. CODING RULE

Before modifying existing files:

1. Inspect the repository.
2. Understand existing implementation.
3. Identify working code.
4. Reuse working logic where possible.
5. Avoid unnecessary rewrites.
6. Make small changes.
7. Run/test the changed code.
8. Fix errors before moving to the next phase.

Do not assume files contain something without reading them.

---

# 45. IMPORTANT: DO NOT DESTROY WORKING CODE

The existing scripts have already been tested.

Do not delete them simply because a FastAPI architecture is being introduced.

If a function from an existing script is useful:

    extract it
    refactor it
    reuse it

rather than blindly rewriting it.

---

# 46. TESTING REQUIREMENTS

After implementing each backend feature, test it.

Minimum tests:

1. Tally connection
2. MySQL connection
3. Ledger extraction
4. Ledger insertion
5. Ledger update/upsert
6. Voucher extraction
7. XML sanitization
8. Voucher parsing
9. Voucher insertion
10. Voucher update
11. Voucher entry insertion
12. Foreign key relationship
13. Duplicate prevention
14. Sync logging
15. Transaction rollback
16. Incremental synchronization

---

# 47. END-TO-END DEMO SCENARIO

The final system must support this demonstration.

STEP 1:

Start TallyPrime.

Open:

    Tally MySQL Integration Demo

STEP 2:

Start MySQL.

STEP 3:

Start FastAPI backend.

STEP 4:

Start React frontend.

STEP 5:

Open dashboard.

STEP 6:

Click:

    Test Tally Connection

Expected:

    Connected

STEP 7:

Click:

    Test MySQL Connection

Expected:

    Connected

STEP 8:

Click:

    Sync Ledgers

Expected:

    Ledger data extracted from Tally and synchronized to MySQL.

STEP 9:

Click:

    Sync Vouchers

Expected:

    Voucher data extracted from Tally.

STEP 10:

Show voucher data in the UI.

STEP 11:

Create a new Payment voucher in Tally.

STEP 12:

Click:

    Incremental Synchronization

STEP 13:

The new voucher should appear in MySQL.

STEP 14:

Run synchronization again.

Expected:

    No duplicate voucher.

The result should demonstrate:

    Tally
      ↓
    XML
      ↓
    Python
      ↓
    Parse
      ↓
    Transform
      ↓
    MySQL
      ↓
    React Dashboard

---

# 48. CURRENT DEMO DATA

The current Tally company contains ledger data and demo payment transactions.

Known demo payment:

    Date:
    02-09-2026

    Voucher Type:
    Payment

    Voucher Number:
    1

    Ledger:
    Rent Expense

    Amount:
    -1000.00

    Ledger:
    Cash

    Amount:
    1000.00

Narration:

    Demo payment for Tally MySQL integration

Another demo payment may exist for incremental synchronization.

Do not hardcode these values into the application.

They are only reference data for testing.

---

# 49. WHAT THE FINAL APPLICATION SHOULD DEMONSTRATE

The final application should clearly demonstrate:

    1. Tally connectivity
    2. MySQL connectivity
    3. Ledger extraction
    4. Voucher extraction
    5. XML parsing
    6. Data transformation
    7. Relational mapping
    8. Database insertion
    9. Database update
    10. Duplicate prevention
    11. Synchronization
    12. Logging
    13. Error handling
    14. User-friendly operation

---

# 50. WHAT NOT TO CLAIM

Do NOT claim:

- Direct access to Tally's internal database
- That Tally automatically provides a MySQL schema
- That every Tally version behaves identically
- That the current system supports every possible Tally object
- That the current incremental sync detects every possible source change perfectly
- That the demo is production-ready without further deployment/security work

Use technically accurate language.

---

# 51. DOCUMENTATION

Create/update README.md with:

- Project overview
- Architecture
- Technologies
- Prerequisites
- Tally configuration
- MySQL configuration
- Environment variables
- Backend setup
- Frontend setup
- How to run
- How synchronization works
- Database schema
- API endpoints
- Demo steps
- Known limitations
- Production considerations

---

# 52. CODE QUALITY

Prefer:

- clear naming
- small functions
- separation of responsibilities
- reusable services
- proper exception handling
- environment configuration
- type hints where useful
- comments for non-obvious logic

Avoid:

- giant files
- duplicated XML parsing code
- duplicated database connection code
- hardcoded credentials
- hardcoded dashboard statistics
- unnecessary dependencies
- unnecessary complexity

---

# 53. FINAL ARCHITECTURE

The target architecture is:

                    OPERATOR
                        |
                        v
               +----------------+
               | React Frontend |
               +-------+--------+
                       |
                     HTTP
                       |
                       v
               +----------------+
               | FastAPI Backend|
               +-------+--------+
                       |
             +---------+---------+
             |                   |
             v                   v
      +-------------+      +-------------+
      | TallyPrime  |      |    MySQL    |
      | XML / HTTP  |      | tally_      |
      | Port 9000   |      | integration |
      +-------------+      +-------------+

The Python backend is the integration/ETL layer.

It is responsible for:

    Extract
    Parse
    Validate
    Transform
    Load
    Synchronize
    Log
    Handle errors

---

# 54. FINAL INSTRUCTION TO CODEX

You are working inside an existing project.

Do not immediately generate a large amount of code.

First inspect the repository and existing scripts.

Then report:

1. Current project structure
2. Existing working functionality
3. Existing Tally integration
4. Existing MySQL integration
5. Existing database/schema
6. Existing synchronization logic
7. What needs to be changed
8. Proposed implementation plan

Then implement the project one phase at a time.

After each significant phase:

- run appropriate tests
- verify the result
- report what changed
- report any issue
- continue only after the current phase is working

Preserve existing working behavior.

The final objective is a working React + FastAPI + TallyPrime + MySQL integration dashboard.

Do not replace the architecture with a different technology stack unless explicitly instructed.

Do not use mock Tally data when the real local Tally instance is available.

Use the actual TallyPrime instance at:

    http://localhost:9000

for integration testing.

The application must be operational through UI buttons rather than requiring the operator to manually execute Python scripts or SQL commands.