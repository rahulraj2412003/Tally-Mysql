import requests
import mysql.connector
import xml.etree.ElementTree as ET
from backend.config import settings
from backend.database.connection import get_mysql_connection


# ==========================================
# 1. TALLY CONNECTION
# ==========================================

TALLY_URL = settings.tally_url


# ==========================================
# 2. TALLY XML REQUEST
# ==========================================

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


# ==========================================
# 3. EXTRACT LEDGERS FROM TALLY
# ==========================================

def extract_ledgers_from_tally():

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

    # --------------------------------------
    # Parse XML
    # --------------------------------------

    root = ET.fromstring(response.text)

    tally_status = root.findtext("./HEADER/STATUS")

    print("Tally Status:", tally_status)

    if tally_status != "1":
        raise RuntimeError("Tally request failed")

    # --------------------------------------
    # Extract ledgers
    # --------------------------------------

    ledgers = []

    for ledger in root.findall(".//LEDGER"):

        # In the current Tally response,
        # ledger name is available as an attribute.
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


# ==========================================
# 4. CONNECT TO MYSQL
# ==========================================

def connect_to_mysql():

    connection = get_mysql_connection()

    print("Connected to MySQL successfully!")

    return connection


# ==========================================
# 5. UPSERT LEDGERS INTO MYSQL
# ==========================================

def save_ledgers_to_mysql(connection, ledgers):

    cursor = connection.cursor()

    # --------------------------------------
    # UPSERT QUERY
    # --------------------------------------
    #
    # If the ledger does not exist:
    #     INSERT
    #
    # If the ledger already exists:
    #     UPDATE parent
    #
    # --------------------------------------

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

    inserted = 0
    updated = 0

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

        # ----------------------------------
        # INSERT / UPDATE
        # ----------------------------------

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
            print(f"Updated ledger: {name}")

        else:
            inserted += 1
            print(f"Inserted ledger: {name}")

    cursor.close()

    return inserted, updated


# ==========================================
# 6. MAIN PROGRAM
# ==========================================

def main():

    print("=" * 60)
    print("TALLY → MYSQL LEDGER SYNCHRONIZATION")
    print("=" * 60)

    connection = None

    try:

        # ----------------------------------
        # Extract from Tally
        # ----------------------------------

        ledgers = extract_ledgers_from_tally()

        print()
        print("Ledgers extracted from Tally:", len(ledgers))

        if not ledgers:

            print("No ledger data found.")

            return

        # ----------------------------------
        # Connect to MySQL
        # ----------------------------------

        connection = connect_to_mysql()

        # ----------------------------------
        # Start transaction
        # ----------------------------------

        connection.start_transaction()

        # ----------------------------------
        # Save data
        # ----------------------------------

        inserted, updated = save_ledgers_to_mysql(
            connection,
            ledgers
        )

        # ----------------------------------
        # Commit
        # ----------------------------------

        connection.commit()

        print()
        print("=" * 60)
        print("SYNCHRONIZATION COMPLETED")
        print("=" * 60)

        print("Total extracted :", len(ledgers))
        print("Inserted        :", inserted)
        print("Updated         :", updated)

    except Exception as error:

        print()
        print("ERROR:", error)

        # ----------------------------------
        # Rollback if transaction failed
        # ----------------------------------

        if connection:
            connection.rollback()

            print("Transaction rolled back.")

    finally:

        # ----------------------------------
        # Close MySQL connection
        # ----------------------------------

        if connection and connection.is_connected():

            connection.close()

            print("MySQL connection closed.")


# ==========================================
# 7. PROGRAM ENTRY POINT
# ==========================================

if __name__ == "__main__":
    main()
