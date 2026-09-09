import requests
import mysql.connector
import xml.etree.ElementTree as ET
import re

from decimal import Decimal
from datetime import datetime, date, timedelta
from backend.config import settings
from backend.database.connection import get_mysql_connection


# ============================================================
# 1. CONFIGURATION
# ============================================================

TALLY_URL = settings.tally_url

COMPANY_NAME = settings.tally_company


# ============================================================
# 2. GET LAST SYNC DATE
# ============================================================

def get_last_sync_date(connection):

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT last_sync_date
        FROM sync_state
        WHERE entity_type = %s
        """,
        ("VOUCHER",)
    )

    result = cursor.fetchone()

    cursor.close()

    if result and result[0]:
        return result[0]

    return None


# ============================================================
# 3. SAVE SYNC STATE
# ============================================================

def save_sync_state(connection, sync_date):

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO sync_state (
            entity_type,
            last_sync_date,
            last_sync_time
        )
        VALUES (%s, %s, %s)

        ON DUPLICATE KEY UPDATE
            last_sync_date = %s,
            last_sync_time = %s
        """,
        (
            "VOUCHER",
            sync_date,
            datetime.now(),
            sync_date,
            datetime.now()
        )
    )

    connection.commit()

    cursor.close()


# ============================================================
# 4. BUILD TALLY REQUEST
# ============================================================

def build_tally_request(from_date, to_date):

    from_date_text = from_date.strftime("%d-%b-%Y")
    to_date_text = to_date.strftime("%d-%b-%Y")

    return f"""
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

                <SVCURRENTCOMPANY>{COMPANY_NAME}</SVCURRENTCOMPANY>

                <SVFROMDATE TYPE="Date">
                    {from_date_text}
                </SVFROMDATE>

                <SVTODATE TYPE="Date">
                    {to_date_text}
                </SVTODATE>

                <SVEXPORTFORMAT>
                    $$SysName:XML
                </SVEXPORTFORMAT>

            </STATICVARIABLES>

        </DESC>

    </BODY>

</ENVELOPE>
"""


# ============================================================
# 5. EXTRACT VOUCHERS FROM TALLY
# ============================================================

def extract_vouchers(from_date, to_date):

    xml_request = build_tally_request(
        from_date,
        to_date
    )

    response = requests.post(
        TALLY_URL,
        data=xml_request,
        headers={
            "Content-Type": "text/xml"
        },
        timeout=30
    )

    response.raise_for_status()

    print("Tally HTTP Status:", response.status_code)

    # --------------------------------------------------------
    # Tally may return invalid XML character references.
    # Remove them before parsing.
    # --------------------------------------------------------

    xml_text = response.text

    xml_text = re.sub(
        r'&#(?:0*4|0*5|0*6|0*7|0*8|0*11|0*12|0*14|0*15|0*16|0*17|0*18|0*19|0*20|0*21|0*22|0*23|0*24|0*25|0*26|0*27|0*28|0*29|0*30|0*31);',
        '',
        xml_text
    )

    xml_text = re.sub(
        r'[\x00-\x08\x0B\x0C\x0E-\x1F]',
        '',
        xml_text
    )

    root = ET.fromstring(xml_text)

    tally_status = root.findtext("./HEADER/STATUS")

    print("Tally Status:", tally_status)

    if tally_status != "1":
        raise RuntimeError(
            "Tally returned an unsuccessful status"
        )

    vouchers = []

    for voucher in root.findall(".//VOUCHER"):

        master_id = voucher.findtext("MASTERID")
        alter_id = voucher.findtext("ALTERID")
        voucher_key = voucher.findtext("VOUCHERKEY")

        date_text = voucher.findtext("DATE")
        voucher_type = voucher.findtext("VOUCHERTYPENAME")
        voucher_number = voucher.findtext("VOUCHERNUMBER")
        narration = voucher.findtext("NARRATION")

        if not voucher_key or not date_text:
            continue

        ledger_entries = []

        for entry in voucher.findall(
            ".//ALLLEDGERENTRIES.LIST"
        ):

            ledger_name = entry.findtext("LEDGERNAME")
            amount_text = entry.findtext("AMOUNT")

            if ledger_name and amount_text:

                ledger_entries.append({
                    "ledger_name": ledger_name.strip(),
                    "amount": Decimal(
                        amount_text.strip()
                    )
                })

        vouchers.append({
            "master_id": (
                master_id.strip()
                if master_id else None
            ),

            "alter_id": (
                alter_id.strip()
                if alter_id else None
            ),

            "voucher_key": (
                voucher_key.strip()
            ),

            "date": date_text.strip(),

            "voucher_type": (
                voucher_type.strip()
                if voucher_type else None
            ),

            "voucher_number": (
                voucher_number.strip()
                if voucher_number else None
            ),

            "narration": (
                narration.strip()
                if narration else None
            ),

            "ledger_entries": ledger_entries
        })

    return vouchers


# ============================================================
# 6. INSERT / UPDATE VOUCHER
# ============================================================

def save_voucher(connection, voucher):

    cursor = connection.cursor()

    voucher_date = datetime.strptime(
        voucher["date"],
        "%Y%m%d"
    ).date()

    # --------------------------------------------------------
    # Check whether voucher already exists
    # --------------------------------------------------------

    cursor.execute(
        """
        SELECT id
        FROM vouchers
        WHERE tally_voucher_key = %s
        """,
        (voucher["voucher_key"],)
    )

    existing = cursor.fetchone()

    # --------------------------------------------------------
    # INSERT
    # --------------------------------------------------------

    if existing is None:

        cursor.execute(
            """
            INSERT INTO vouchers (
                tally_master_id,
                tally_alter_id,
                tally_voucher_key,
                voucher_date,
                voucher_type,
                voucher_number,
                narration
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s
            )
            """,
            (
                voucher["master_id"],
                voucher["alter_id"],
                voucher["voucher_key"],
                voucher_date,
                voucher["voucher_type"],
                voucher["voucher_number"],
                voucher["narration"]
            )
        )

        voucher_id = cursor.lastrowid

        action = "INSERTED"

    # --------------------------------------------------------
    # UPDATE
    # --------------------------------------------------------

    else:

        voucher_id = existing[0]

        cursor.execute(
            """
            UPDATE vouchers
            SET
                tally_master_id = %s,
                tally_alter_id = %s,
                voucher_date = %s,
                voucher_type = %s,
                voucher_number = %s,
                narration = %s
            WHERE id = %s
            """,
            (
                voucher["master_id"],
                voucher["alter_id"],
                voucher_date,
                voucher["voucher_type"],
                voucher["voucher_number"],
                voucher["narration"],
                voucher_id
            )
        )

        action = "UPDATED"

    # --------------------------------------------------------
    # Remove existing entries
    # --------------------------------------------------------

    cursor.execute(
        """
        DELETE FROM voucher_entries
        WHERE voucher_id = %s
        """,
        (voucher_id,)
    )

    # --------------------------------------------------------
    # Insert current entries
    # --------------------------------------------------------

    for entry in voucher["ledger_entries"]:

        cursor.execute(
            """
            SELECT id
            FROM ledgers
            WHERE name = %s
            LIMIT 1
            """,
            (entry["ledger_name"],)
        )

        ledger = cursor.fetchone()

        if ledger is None:

            print(
                "WARNING: Ledger not found:",
                entry["ledger_name"]
            )

            continue

        ledger_id = ledger[0]

        cursor.execute(
            """
            INSERT INTO voucher_entries (
                voucher_id,
                ledger_id,
                amount
            )
            VALUES (%s, %s, %s)
            """,
            (
                voucher_id,
                ledger_id,
                entry["amount"]
            )
        )

    cursor.close()

    return action


# ============================================================
# 7. CREATE SYNC LOG
# ============================================================

def create_sync_log(connection):

    cursor = connection.cursor()

    started_at = datetime.now()

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
            "VOUCHER",
            started_at,
            "RUNNING"
        )
    )

    sync_id = cursor.lastrowid

    connection.commit()

    cursor.close()

    return sync_id


# ============================================================
# 8. UPDATE SYNC LOG
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
            datetime.now(),
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
# 9. MAIN
# ============================================================

def main():

    print("=" * 60)
    print("TALLY → MYSQL INCREMENTAL VOUCHER SYNC")
    print("=" * 60)

    connection = None
    sync_id = None

    extracted = 0
    inserted = 0
    updated = 0
    failed = 0

    try:

        # ----------------------------------------------------
        # Connect MySQL
        # ----------------------------------------------------

        connection = get_mysql_connection()

        print("Connected to MySQL successfully!")

        # ----------------------------------------------------
        # Create log
        # ----------------------------------------------------

        sync_id = create_sync_log(
            connection
        )

        print("Sync ID:", sync_id)

        # ----------------------------------------------------
        # Get previous checkpoint
        # ----------------------------------------------------

        last_sync_date = get_last_sync_date(
            connection
        )

        today = date.today()

        if last_sync_date is None:

            # ----------------------------------------------
            # FIRST RUN
            # ----------------------------------------------

            from_date = date(2026, 4, 1)

            sync_mode = "INITIAL"

        else:

            # ----------------------------------------------
            # SUBSEQUENT RUN
            # ----------------------------------------------

            from_date = last_sync_date

            sync_mode = "INCREMENTAL"

        to_date = today

        print("Sync mode:", sync_mode)
        print("From date:", from_date)
        print("To date  :", to_date)

        # ----------------------------------------------------
        # Extract
        # ----------------------------------------------------

        vouchers = extract_vouchers(
            from_date,
            to_date
        )

        extracted = len(vouchers)

        print(
            "Vouchers extracted:",
            extracted
        )

        # ----------------------------------------------------
        # Load into MySQL
        # ----------------------------------------------------

        # connection.start_transaction()

        for voucher in vouchers:

            try:

                action = save_voucher(
                    connection,
                    voucher
                )

                if action == "INSERTED":
                    inserted += 1

                elif action == "UPDATED":
                    updated += 1

            except Exception as error:

                failed += 1

                print(
                    "Voucher failed:",
                    voucher.get("voucher_key"),
                    error
                )

        # ----------------------------------------------------
        # If individual records failed,
        # rollback the complete transaction.
        # ----------------------------------------------------

        if failed > 0:

            raise RuntimeError(
                f"{failed} voucher(s) failed"
            )

        # ----------------------------------------------------
        # Commit
        # ----------------------------------------------------

        connection.commit()

        # ----------------------------------------------------
        # Update checkpoint ONLY after successful commit
        # ----------------------------------------------------

        save_sync_state(
            connection,
            to_date
        )

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

        print()
        print("=" * 60)
        print("SYNCHRONIZATION SUCCESSFUL")
        print("=" * 60)

        print("Extracted:", extracted)
        print("Inserted :", inserted)
        print("Updated  :", updated)
        print("Failed   :", failed)

    except Exception as error:

        print()
        print("ERROR:", error)

        if connection:

            connection.rollback()

            print("Transaction rolled back.")

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

    finally:

        if connection and connection.is_connected():

            connection.close()

            print("MySQL connection closed.")


# ============================================================
# 10. ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
