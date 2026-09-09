"""Utilities for Tally responses that are not valid XML 1.0 as returned."""

import re


INVALID_NUMERIC_REFERENCES = re.compile(
    r"&#(?:0*4|0*5|0*6|0*7|0*8|0*11|0*12|0*14|0*15|0*16|0*17|"
    r"0*18|0*19|0*20|0*21|0*22|0*23|0*24|0*25|0*26|0*27|0*28|"
    r"0*29|0*30|0*31);"
)
RAW_INVALID_XML_CHARACTERS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")


def sanitize_tally_xml(xml_text: str) -> str:
    """Remove XML 1.0-invalid control references and raw control characters."""
    without_invalid_references = INVALID_NUMERIC_REFERENCES.sub("", xml_text)
    return RAW_INVALID_XML_CHARACTERS.sub("", without_invalid_references)

