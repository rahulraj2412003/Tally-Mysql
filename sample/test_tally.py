import requests
import xml.etree.ElementTree as ET
from backend.config import settings

# Tally server
url = settings.tally_url

# XML request
xml_request = """
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

# Send request
response = requests.post(
    url,
    data=xml_request,
    headers={
        "Content-Type": "text/xml"
    },
    timeout=30
)

# Check HTTP status
response.raise_for_status()

print("HTTP Status:", response.status_code)

# Convert XML response into XML tree
root = ET.fromstring(response.text)

# Check Tally status
status = root.findtext("./HEADER/STATUS")

print("Tally Status:", status)

if status != "1":
    raise RuntimeError("Tally request failed")


# -----------------------------------------
# Extract ledger data
# -----------------------------------------

ledgers = []

for ledger in root.findall(".//LEDGER"):

    # NAME is an XML attribute
    name = ledger.get("NAME")

    # Parent may not be returned by this collection
    parent = ledger.findtext("PARENT")

    # Ignore empty/metadata ledger elements
    if not name:
        continue

    ledgers.append({
        "name": name
        
    })


# -----------------------------------------
# Display data
# -----------------------------------------

print("\nExtracted Ledgers:")
print("-" * 60)

for ledger in ledgers:
    print(
        f"Name: {ledger['name']}"
        
    )

print("-" * 60)
print("Total Ledgers:", len(ledgers))
