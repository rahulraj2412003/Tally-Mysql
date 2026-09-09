import requests
import xml.etree.ElementTree as ET
import re
from backend.config import settings


# ============================================================
# 1. TALLY CONNECTION
# ============================================================

TALLY_URL = settings.tally_url


# ============================================================
# 2. TALLY XML REQUEST
# ============================================================

xml_request = """
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

                <SVCURRENTCOMPANY>
                    Tally MySQL Integration Demo
                </SVCURRENTCOMPANY>

                <SVFROMDATE TYPE="Date">
                    20260902
                </SVFROMDATE>

                <SVTODATE TYPE="Date">
                    20260902
                </SVTODATE>

                <SVEXPORTFORMAT>
                    $$SysName:XML
                </SVEXPORTFORMAT>

            </STATICVARIABLES>

            <FETCHLIST>

                <FETCH>MASTERID</FETCH>
                <FETCH>ALTERID</FETCH>
                <FETCH>VOUCHERKEY</FETCH>
                <FETCH>DATE</FETCH>
                <FETCH>VOUCHERTYPENAME</FETCH>
                <FETCH>VOUCHERNUMBER</FETCH>
                <FETCH>NARRATION</FETCH>

            </FETCHLIST>

        </DESC>

    </BODY>

</ENVELOPE>
"""


# ============================================================
# 3. SEND REQUEST TO TALLY
# ============================================================

try:

    response = requests.post(
        TALLY_URL,
        data=xml_request,
        headers={
            "Content-Type": "text/xml"
        },
        timeout=30
    )

    response.raise_for_status()

except requests.exceptions.RequestException as e:

    print("ERROR: Could not connect to Tally.")
    print(e)
    raise SystemExit


print("HTTP Status:", response.status_code)


# ============================================================
# 4. CLEAN TALLY XML
# ============================================================

xml_text = response.text

# Tally can return invalid XML character references
# such as &#4;.
#
# XML 1.0 does not allow these control characters.

xml_text = re.sub(
    r'&#(?:0*4|0*5|0*6|0*7|0*8|0*11|0*12|0*14|0*15|0*16|0*17|0*18|0*19|0*20|0*21|0*22|0*23|0*24|0*25|0*26|0*27|0*28|0*29|0*30|0*31);',
    '',
    xml_text
)

# Remove raw invalid XML control characters

xml_text = re.sub(
    r'[\x00-\x08\x0B\x0C\x0E-\x1F]',
    '',
    xml_text
)


# ============================================================
# 5. PARSE XML
# ============================================================

try:

    root = ET.fromstring(xml_text)

except ET.ParseError as e:

    print("\nERROR: Tally returned invalid XML.")
    print(e)

    # Save response for debugging
    with open(
        "tally_voucher_response.xml",
        "w",
        encoding="utf-8"
    ) as file:

        file.write(xml_text)

    print(
        "\nThe cleaned Tally response has been saved as:"
        "\ntally_voucher_response.xml"
    )

    raise SystemExit


# ============================================================
# 6. CHECK TALLY STATUS
# ============================================================

tally_status = root.findtext("./HEADER/STATUS")

print("Tally Status:", tally_status)

if tally_status != "1":

    print("\nERROR: Tally did not process the request successfully.")

    # Try to display an error message if Tally provided one
    error_message = root.findtext(".//LINEERROR")

    if error_message:
        print("Tally Error:", error_message)

    raise SystemExit


# ============================================================
# 7. FIND VOUCHERS
# ============================================================

vouchers = root.findall(".//VOUCHER")

print("\nVouchers found:", len(vouchers))


# ============================================================
# 8. PROCESS EACH VOUCHER
# ============================================================

for index, voucher in enumerate(vouchers, start=1):

    print("\n" + "=" * 60)

    print(f"VOUCHER {index}")

    print("=" * 60)


    # --------------------------------------------------------
    # Voucher Header
    # --------------------------------------------------------

    master_id = voucher.findtext("MASTERID")
    alter_id = voucher.findtext("ALTERID")
    voucher_key = voucher.findtext("VOUCHERKEY")

    date = voucher.findtext("DATE")

    voucher_type = voucher.findtext("VOUCHERTYPENAME")

    voucher_number = voucher.findtext("VOUCHERNUMBER")

    narration = voucher.findtext("NARRATION")


    # --------------------------------------------------------
    # Display Header
    # --------------------------------------------------------

    print("Master ID     :", master_id)
    print("Alter ID      :", alter_id)
    print("Voucher Key   :", voucher_key)
    print("Date          :", date)
    print("Voucher Type  :", voucher_type)
    print("Voucher Number:", voucher_number)
    print("Narration     :", narration)


    # --------------------------------------------------------
    # Ledger Entries
    # --------------------------------------------------------

    print("\nLedger Entries")
    print("-" * 60)


    ledger_entries = voucher.findall(
        "ALLLEDGERENTRIES.LIST"
    )


    if not ledger_entries:

        print("No ledger entries found.")


    for entry_number, entry in enumerate(
        ledger_entries,
        start=1
    ):

        ledger_name = entry.findtext(
            "LEDGERNAME"
        )

        amount = entry.findtext(
            "AMOUNT"
        )


        print(
            f"{entry_number}. "
            f"Ledger: {ledger_name} "
            f"| Amount: {amount}"
        )


# ============================================================
# 9. FINISHED
# ============================================================

print("\n" + "=" * 60)
print("Extraction completed successfully.")
print("=" * 60)
