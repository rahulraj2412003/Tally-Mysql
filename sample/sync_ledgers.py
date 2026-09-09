import requests
import mysql.connector
import xml.etree.ElementTree as ET
from datetime import datetime
from backend.config import settings
from backend.database.connection import get_mysql_connection


# ============================================================
# 1. TALLY CONFIGURATION
# ============================================================

TALLY_URL = settings.tally_url


XML_REQUEST = """
<ENVELOPE>
    <HEADER>
        <VERSION>1</VERSION>
        <TALLYREQUEST>EXPORT</TALLYREQUEST>
        <TYPE>COLLECTION</TYPE>
        <ID>List of Ledgers</ID>
    </HEADER>

    <BODY>
        <DESC>

            <STATICVARIABLES>
                <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
            </STATICVARIABLES>

            <FETCHLIST>
                <FETCH>Name</FETCH>
                <FETCH>Parent</FETCH>
            </FETCHLIST>

        </DESC>
    </BODY>
</ENVELOPE>
"""


# ============================================================
# 2. MYSQL CONNECTION
# ============================================================

def connect_to_mysql():

    return get_mysql_connection()


# ============================================================
# 3. CREATE SYNC LOG
# ============================================================

def create_sync_log(connection, started_at):

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO sync_log (
            sync_type,
            started_at,
            status
        )
        VALUES (%s, %s, %s)
        """,
        (
            "LEDGER",
            started_at,
            "RUNNING"
        )
    )

    sync_id = cursor.lastrowid

    connection.commit()

    cursor.close()

    return sync_id


# ============================================================
# 4. UPDATE SYNC LOG
# ============================================================

def update_sync_log(
    connection,
    sync_id,
    status,
    extracted,
    inserted,
    updated,
    failed,
    error_message=None
):

    cursor = connection.cursor()

    completed_at = datetime.now()

    cursor.execute(
        """
        UPDATE sync_log
        SET
            completed_at = %s,
            records_extracted = %s,
            records_inserted = %s,
            records_updated = %s,
            records_failed = %s,
            status = %s,
            error_message = %s
        WHERE id = %s
        """,
        (
            completed_at,
            extracted,
            inserted,
            updated,
            failed,
            status,
            error_message,
            sync_id
        )
    )

    connection.commit()

    cursor.close()


# ============================================================
# 5. EXTRACT LEDGERS FROM TALLY
# ============================================================

def extract_ledgers():

    response = requests.post(
        TALLY_URL,
        data=XML_REQUEST,
        headers={
            "Content-Type": "text/xml"
        },
        timeout=30
    )

    response.raise_for_status()

    print("Tally HTTP Status:", response.status_code)

    root = ET.fromstring(response.text)

    tally_status = root.findtext("./HEADER/STATUS")

    print("Tally Status:", tally_status)

    if tally_status != "1":

        raise RuntimeError(
            "Tally returned an unsuccessful status"
        )

    ledgers = []

    for ledger in root.findall(".//LEDGER"):

        name = ledger.get("NAME")

        if not name:
            continue

        name = name.strip()

        parent = ledger.findtext("PARENT")

        if parent:
            parent = parent.strip()

        ledgers.append({
            "name": name,
            "parent": parent
        })

    return ledgers


# ============================================================
# 6. SAVE LEDGERS
# ============================================================

def save_ledgers(connection, ledgers):

    cursor = connection.cursor()

    inserted = 0
    updated = 0

    upsert_query = """
        INSERT INTO ledgers (
            name,
            parent
        )
        VALUES (%s, %s)

        ON DUPLICATE KEY UPDATE
            parent = %s,
            updated_at = CURRENT_TIMESTAMP
    """

    for ledger in ledgers:

        name = ledger["name"]
        parent = ledger["parent"]

        # Check whether ledger already exists
        cursor.execute(
            """
            SELECT id
            FROM ledgers
            WHERE name = %s
            """,
            (name,)
        )

        existing = cursor.fetchone()

        # Insert or update
        cursor.execute(
            upsert_query,
            (
                name,
                parent,
                parent
            )
        )

        if existing:

            updated += 1

        else:

            inserted += 1

    cursor.close()

    return inserted, updated


# ============================================================
# 7. MAIN
# ============================================================

def main():

    print("=" * 60)
    print("TALLY → MYSQL LEDGER SYNC")
    print("=" * 60)

    connection = None
    sync_id = None

    started_at = datetime.now()

    extracted = 0
    inserted = 0
    updated = 0
    failed = 0

    try:

        # ----------------------------------------------------
        # Connect to MySQL
        # ----------------------------------------------------

        connection = connect_to_mysql()

        print("Connected to MySQL successfully!")

        # ----------------------------------------------------
        # Create sync log
        # ----------------------------------------------------

        sync_id = create_sync_log(
            connection,
            started_at
        )

        print("Sync ID:", sync_id)

        # ----------------------------------------------------
        # Extract from Tally
        # ----------------------------------------------------

        ledgers = extract_ledgers()

        extracted = len(ledgers)

        print(
            "Ledgers extracted:",
            extracted
        )

        # ----------------------------------------------------
        # Start transaction for data loading
        # ----------------------------------------------------

        connection.start_transaction()

        inserted, updated = save_ledgers(
            connection,
            ledgers
        )

        # ----------------------------------------------------
        # Commit data
        # ----------------------------------------------------

        connection.commit()

        print()
        print("Ledger synchronization successful!")

        print("Inserted:", inserted)
        print("Updated :", updated)

        # ----------------------------------------------------
        # Update sync log
        # ----------------------------------------------------

        update_sync_log(
            connection,
            sync_id,
            "SUCCESS",
            extracted,
            inserted,
            updated,
            failed
        )

        print("Sync log updated successfully.")

    except Exception as error:

        print()
        print("ERROR:", error)

        failed = 1

        # ----------------------------------------------------
        # Rollback data transaction
        # ----------------------------------------------------

        if connection:

            connection.rollback()

            print("Transaction rolled back.")

        # ----------------------------------------------------
        # Log failure
        # ----------------------------------------------------

        if connection and sync_id:

            update_sync_log(
                connection,
                sync_id,
                "FAILED",
                extracted,
                inserted,
                updated,
                failed,
                str(error)
            )

            print("Failure recorded in sync_log.")

    finally:

        if connection and connection.is_connected():

            connection.close()

            print("MySQL connection closed.")


# ============================================================
# 8. PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
