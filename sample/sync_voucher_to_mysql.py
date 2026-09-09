import requests
import xml.etree.ElementTree as ET
import re
import mysql.connector
from decimal import Decimal
from datetime import datetime
from backend.config import settings
from backend.database.connection import get_mysql_connection


# ============================================================
# 1. TALLY CONFIGURATION
# ============================================================

TALLY_URL = settings.tally_url

TALLY_XML = """
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
                <SVFROMDATE TYPE="Date">02-Sep-2026</SVFROMDATE>
                <SVTODATE TYPE="Date">02-Sep-2026</SVTODATE>
                <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
            </STATICVARIABLES>
        </DESC>
    </BODY>
</ENVELOPE>
"""


# ============================================================
# 2. EXTRACT VOUCHER FROM TALLY
# ============================================================

def extract_vouchers():

    response = requests.post(
        TALLY_URL,
        data=TALLY_XML,
        headers={"Content-Type": "text/xml"},
        timeout=30
    )

    response.raise_for_status()

    print("Tally HTTP Status:", response.status_code)

    # Tally sometimes returns invalid XML character references
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
        raise RuntimeError("Tally returned an unsuccessful status")

    vouchers = []

    for voucher in root.findall(".//VOUCHER"):

        master_id = voucher.findtext("MASTERID")
        alter_id = voucher.findtext("ALTERID")
        voucher_key = voucher.findtext("VOUCHERKEY")

        date_text = voucher.findtext("DATE")
        voucher_type = voucher.findtext("VOUCHERTYPENAME")
        voucher_number = voucher.findtext("VOUCHERNUMBER")
        narration = voucher.findtext("NARRATION")

        ledger_entries = []

        for entry in voucher.findall(".//ALLLEDGERENTRIES.LIST"):

            ledger_name = entry.findtext("LEDGERNAME")
            amount_text = entry.findtext("AMOUNT")

            if ledger_name and amount_text:

                ledger_entries.append({
                    "ledger_name": ledger_name.strip(),
                    "amount": Decimal(amount_text.strip())
                })

        vouchers.append({
            "master_id": master_id.strip() if master_id else None,
            "alter_id": alter_id.strip() if alter_id else None,
            "voucher_key": voucher_key.strip() if voucher_key else None,
            "date": date_text.strip() if date_text else None,
            "voucher_type": voucher_type.strip() if voucher_type else None,
            "voucher_number": voucher_number.strip() if voucher_number else None,
            "narration": narration.strip() if narration else None,
            "ledger_entries": ledger_entries
        })

    return vouchers


# ============================================================
# 3. CONNECT TO MYSQL
# ============================================================

def connect_mysql():

    connection = get_mysql_connection()

    print("Connected to MySQL successfully!")

    return connection


# ============================================================
# 4. SYNCHRONIZE VOUCHER
# ============================================================

def sync_voucher(connection, voucher):

    cursor = connection.cursor()

    # --------------------------------------------------------
    # Convert Tally date: 20260902 → 2026-09-02
    # --------------------------------------------------------

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
    # INSERT new voucher
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
            VALUES (%s, %s, %s, %s, %s, %s, %s)
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

        print(
            f"Voucher inserted: "
            f"{voucher['voucher_type']} #{voucher['voucher_number']}"
        )

    # --------------------------------------------------------
    # UPDATE existing voucher
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

        print(
            f"Voucher updated: "
            f"{voucher['voucher_type']} #{voucher['voucher_number']}"
        )

    # --------------------------------------------------------
    # Remove old voucher entries
    #
    # This makes synchronization idempotent.
    # --------------------------------------------------------

    cursor.execute(
        """
        DELETE FROM voucher_entries
        WHERE voucher_id = %s
        """,
        (voucher_id,)
    )

    # --------------------------------------------------------
    # Insert current voucher entries
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
                f"WARNING: Ledger not found: "
                f"{entry['ledger_name']}"
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


# ============================================================
# 5. MAIN PROGRAM
# ============================================================

def main():

    print("=" * 60)
    print("TALLY → MYSQL VOUCHER SYNCHRONIZATION")
    print("=" * 60)

    try:

        # Extract from Tally
        vouchers = extract_vouchers()

        print("Vouchers extracted:", len(vouchers))

        if not vouchers:
            print("No vouchers found.")
            return

        # Connect MySQL
        connection = connect_mysql()

        try:

            # Start transaction
            connection.start_transaction()

            for voucher in vouchers:
                sync_voucher(connection, voucher)

            # Save everything
            connection.commit()

            print("Transaction committed successfully!")

        except Exception:

            # Undo partial changes
            connection.rollback()

            print("Transaction failed. Changes rolled back.")

            raise

        finally:

            connection.close()

            print("MySQL connection closed.")

    except Exception as error:

        print("ERROR:", error)


if __name__ == "__main__":
    main()
