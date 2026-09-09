"""Connection checks used by API routes and command-line health checks."""

from backend.database.connection import test_mysql_connection
from backend.services.tally_service import TallyClient, build_ledger_request
from backend.services.xml_parser import extract_ledgers, parse_tally_response


def check_tally_connection() -> int:
    """Test Tally and validate that its ledger response can be parsed."""
    xml_text = TallyClient().export(build_ledger_request())
    return len(extract_ledgers(parse_tally_response(xml_text)))


def check_mysql_connection() -> None:
    """Test the MySQL connection with a minimal read-only query."""
    test_mysql_connection()
