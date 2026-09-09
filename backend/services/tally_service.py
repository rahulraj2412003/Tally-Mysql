"""TallyPrime XML-over-HTTP transport and request builders."""

from datetime import date
from xml.sax.saxutils import escape

import requests

from backend.config import settings
from backend.utils.xml_utils import sanitize_tally_xml


class TallyConnectionError(RuntimeError):
    """Raised when TallyPrime cannot be reached or returns invalid HTTP."""


def build_ledger_request() -> str:
    return """
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
""".strip()


def build_day_book_request(from_date: date, to_date: date) -> str:
    company = escape(settings.tally_company)
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
                <SVCURRENTCOMPANY>{company}</SVCURRENTCOMPANY>
                <SVFROMDATE TYPE="Date">{from_date.strftime('%d-%b-%Y')}</SVFROMDATE>
                <SVTODATE TYPE="Date">{to_date.strftime('%d-%b-%Y')}</SVTODATE>
                <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
            </STATICVARIABLES>
        </DESC>
    </BODY>
</ENVELOPE>
""".strip()


class TallyClient:
    def __init__(self, url: str = settings.tally_url, timeout: int = settings.tally_timeout_seconds):
        self.url = url
        self.timeout = timeout

    def export(self, request_xml: str) -> str:
        try:
            response = requests.post(
                self.url,
                data=request_xml,
                headers={"Content-Type": "text/xml"},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise TallyConnectionError(f"Could not communicate with Tally at {self.url}: {error}") from error
        return sanitize_tally_xml(response.text)

    def test_connection(self) -> None:
        """Use the proven ledger-export request as the Tally connection check."""
        self.export(build_ledger_request())

