"""Centralized conversion of Tally date text to Python dates."""

from datetime import date, datetime


def parse_tally_date(value: str) -> date:
    """Convert Tally's YYYYMMDD date format into a ``date`` instance."""
    try:
        return datetime.strptime(value.strip(), "%Y%m%d").date()
    except (AttributeError, ValueError) as error:
        raise ValueError(f"Invalid Tally date {value!r}; expected YYYYMMDD.") from error

