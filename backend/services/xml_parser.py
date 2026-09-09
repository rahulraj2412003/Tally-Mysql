"""XML parsing and source-structure extraction for Tally responses."""

from decimal import Decimal, InvalidOperation
import xml.etree.ElementTree as ET


class TallyXmlParseError(ValueError):
    """Raised when Tally sends malformed or unsuccessful XML."""


def parse_tally_response(xml_text: str) -> ET.Element:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as error:
        raise TallyXmlParseError(f"Tally returned malformed XML: {error}") from error

    if root.findtext("./HEADER/STATUS") != "1":
        message = root.findtext(".//LINEERROR") or "Tally returned an unsuccessful status."
        raise TallyXmlParseError(message.strip())
    return root


def extract_ledgers(root: ET.Element) -> list[dict[str, str | None]]:
    ledgers: list[dict[str, str | None]] = []
    for ledger in root.findall(".//LEDGER"):
        name = ledger.get("NAME")
        if not name or not name.strip():
            continue
        parent = ledger.findtext("PARENT")
        ledgers.append({"name": name.strip(), "parent": parent.strip() if parent else None})
    return ledgers


def extract_vouchers(root: ET.Element) -> list[dict[str, object]]:
    vouchers: list[dict[str, object]] = []
    for voucher in root.findall(".//VOUCHER"):
        voucher_key = _text(voucher, "VOUCHERKEY")
        date_text = _text(voucher, "DATE")
        if not voucher_key or not date_text:
            continue

        entries: list[dict[str, object]] = []
        accounting_entry_tags = {
            "ALLLEDGERENTRIES.LIST",
            "LEDGERENTRIES.LIST",
            "ACCOUNTINGALLOCATIONS.LIST",
        }
        for entry in voucher.iter():
            if entry.tag not in accounting_entry_tags:
                continue
            ledger_name = _text(entry, "LEDGERNAME")
            amount_text = _text(entry, "AMOUNT")
            if not ledger_name or amount_text is None:
                continue
            try:
                amount = Decimal(amount_text)
            except InvalidOperation as error:
                raise TallyXmlParseError(
                    f"Invalid amount {amount_text!r} for ledger {ledger_name!r}."
                ) from error
            entries.append({"ledger_name": ledger_name, "amount": amount})

        vouchers.append({
            "master_id": _text(voucher, "MASTERID"),
            "alter_id": _text(voucher, "ALTERID"),
            "voucher_key": voucher_key,
            "date": date_text,
            "voucher_type": _text(voucher, "VOUCHERTYPENAME"),
            "voucher_number": _text(voucher, "VOUCHERNUMBER"),
            "narration": _text(voucher, "NARRATION"),
            "ledger_entries": entries,
        })
    return vouchers


def _text(element: ET.Element, tag: str) -> str | None:
    value = element.findtext(tag)
    return value.strip() if value and value.strip() else None

