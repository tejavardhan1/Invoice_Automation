import re
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class LineItem:
    description: str
    amount: float


@dataclass
class ExtractedFields:
    vendor: Optional[str]
    invoice_number: Optional[str]
    date: Optional[str]
    currency: Optional[str]
    subtotal: Optional[float]
    tax: Optional[float]
    total: Optional[float]
    line_items: List[LineItem]

    def to_dict(self) -> Dict[str, Any]:
        return {
            **{k: v for k, v in asdict(self).items() if k != "line_items"},
            "line_items": [asdict(li) for li in self.line_items],
        }


def _extract_first_match(pattern: str, text: str, flags: int = re.IGNORECASE) -> Optional[str]:
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else None


def _parse_float(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    cleaned = re.sub(r"[^\d.,-]", "", value).replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _extract_vendor(text: str, lines: List[str]) -> Optional[str]:
    m = re.search(r"(?:From|Vendor|Bill\s*From|Sold\s*By)[:\s]+([^\n]+)", text, re.IGNORECASE)
    if m:
        cand = m.group(1).strip()
        if 2 < len(cand) < 80:
            return cand
    for line in lines[:5]:
        line = line.strip()
        if not line or re.match(r"^[\d\s\/\-\.\$€£]+$", line) or re.match(r"^(Invoice|Date|Total|Subtotal|Tax)", line, re.I):
            continue
        if 2 < len(line) < 80:
            return line
    return lines[0] if lines else None


def extract_fields_from_text(text: str) -> ExtractedFields:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    vendor = _extract_vendor(text, lines)

    raw_inv = (
        _extract_first_match(r"(?:Invoice\s*#?|Inv\s*No\.?|Invoice\s*Number|Ref\s*#?|ID\s*#?)\s*[:\s]*([A-Za-z0-9\-\/]+)", text)
        or _extract_first_match(r"\b([A-Z]{2,5}[\-\s]?\d{4,})\b", text)
    )
    invoice_number = None if (raw_inv and raw_inv.lower() in ("invoice", "number", "no")) else raw_inv

    date_str: Optional[str] = None
    for pattern in [
        r"(?:Date|Invoice\s*Date|Due\s*Date)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        r"(?:Date)[:\s]*(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})",
        r"\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})\b",
    ]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            date_str = m.group(1)
            break

    parsed_date: Optional[str] = None
    if date_str:
        for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y", "%d/%m/%y", "%m/%d/%y"):
            try:
                parsed_date = datetime.strptime(date_str, fmt).date().isoformat()
                break
            except ValueError:
                continue

    currency_match = re.search(r"(\$|€|£|₹|INR|USD|EUR|GBP)", text)
    currency = currency_match.group(1) if currency_match else None

    subtotal_str = _extract_first_match(r"\bSubtotal[:\s]*([0-9\.,]+)", text)
    tax_str = _extract_first_match(r"\b(?:Tax|VAT|GST)[:\s]*([0-9\.,]+)", text)
    total_str = (
        _extract_first_match(r"\bTotal\s*(?:Amount)?[:\s]*([0-9\.,]+)", text)
        or _extract_first_match(r"\b(?:Grand\s*)?Total[:\s]*([0-9\.,]+)", text)
        or _extract_first_match(r"\bAmount\s*Due[:\s]*([0-9\.,]+)", text)
        or _extract_first_match(r"\bNet\s*Amount[:\s]*([0-9\.,]+)", text)
        or _extract_first_match(r"\bBalance\s*(?:Due)?[:\s]*([0-9\.,]+)", text)
        or _extract_first_match(r"(?:Total|Amount)[:\s]*[\$€£₹\s]*([0-9,]+\.?[0-9]*)", text)
        or _extract_first_match(r"[\$€£₹]\s*([0-9,]+\.?[0-9]*)\s*$", text)
    )

    subtotal = _parse_float(subtotal_str)
    tax = _parse_float(tax_str)
    total = _parse_float(total_str)

    line_items: List[LineItem] = []
    for line in lines:
        m = re.search(r"(.+?)\s+([\$€£₹]?\s*[0-9,]+\.?[0-9]{0,2})\s*$", line)
        if m:
            desc, amt_str = m.groups()
            amt = _parse_float(amt_str)
            if amt is not None and len(desc.strip()) > 0:
                line_items.append(LineItem(description=desc.strip(), amount=amt))

    if total is None and line_items:
        total = round(sum(li.amount for li in line_items), 2)

    return ExtractedFields(
        vendor=vendor,
        invoice_number=invoice_number,
        date=parsed_date or date_str,
        currency=currency,
        subtotal=subtotal,
        tax=tax,
        total=total,
        line_items=line_items,
    )


__all__ = ["ExtractedFields", "LineItem", "extract_fields_from_text"]
