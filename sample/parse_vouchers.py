import requests
import xml.etree.ElementTree as ET
import re
from pprint import pprint


# ============================================================
# TALLY CONNECTION
# ============================================================

TALLY_URL = settings.tally_url


# ============================================================
# TALLY REQUEST
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

        </DESC>

    </BODY>

</ENVELOPE>
"""


# ============================================================
# EXTRACT
# ============================================================

response = requests.post(
    TALLY_URL,
    data=xml_request,
    headers={
        "Content-Type": "text/xml"
    },
    timeout=30
)

response.raise_for_status()

print("HTTP Status:", response.status_code)


# ============================================================
# CLEAN XML
# ============================================================

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


# ============================================================
# PARSE XML
# ============================================================

root = ET.fromstring(xml_text)

tally_status = root.findtext("./HEADER/STATUS")

print("Tally Status:", tally_status)

if tally_status != "1":
    raise RuntimeError("Tally request failed")


# ============================================================
# EXTRACT VOUCHERS
# ============================================================

vouchers = []

for voucher in root.findall(".//VOUCHER"):

    voucher_data = {
        "master_id": voucher.findtext("MASTERID"),
        "alter_id": voucher.findtext("ALTERID"),
        "voucher_key": voucher.findtext("VOUCHERKEY"),
        "date": voucher.findtext("DATE"),
        "voucher_type": voucher.findtext("VOUCHERTYPENAME"),
        "voucher_number": voucher.findtext("VOUCHERNUMBER"),
        "narration": voucher.findtext("NARRATION"),
        "ledger_entries": []
    }


    # --------------------------------------------------------
    # Ledger entries
    # --------------------------------------------------------

    for entry in voucher.findall(
        "ALLLEDGERENTRIES.LIST"
    ):

        ledger_name = entry.findtext(
            "LEDGERNAME"
        )

        amount_text = entry.findtext(
            "AMOUNT"
        )


        # Convert amount from string → float

        try:
            amount = float(amount_text)

        except (TypeError, ValueError):
            amount = 0.0


        voucher_data["ledger_entries"].append({

            "ledger_name": ledger_name,

            "amount": amount

        })


    vouchers.append(voucher_data)


# ============================================================
# DISPLAY CLEAN DATA
# ============================================================

print("\nClean Python Data")
print("=" * 60)

print(f"Total vouchers: {len(vouchers)}")

for voucher in vouchers:

    pprint(voucher)
