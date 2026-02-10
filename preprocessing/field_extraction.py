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


def extract_fields_from_text(text: str) -> ExtractedFields:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    vendor = lines[0] if lines else None

    invoice_number = _extract_first_match(r"(?:Invoice\s*#?|Inv\s*No\.?)\s*([A-Za-z0-9\-\/]+)", text)

    date_match = re.search(
        r"\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})\b",
        text,
    )
    date_str: Optional[str] = date_match.group(1) if date_match else None

    parsed_date: Optional[str] = None
    if date_str:
        for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y"):
            try:
                parsed_date = datetime.strptime(date_str, fmt).date().isoformat()
                break
            except ValueError:
                continue

    currency_match = re.search(r"(\$|€|£|INR|USD|EUR|GBP)", text)
    currency = currency_match.group(1) if currency_match else None

    subtotal_str = _extract_first_match(r"\bSubtotal[:\s]*([0-9\.,]+)", text)
    tax_str = _extract_first_match(r"\b(?:Tax|VAT)[:\s]*([0-9\.,]+)", text)
    total_str = _extract_first_match(r"\bTotal[:\s]*([0-9\.,]+)", text)

    subtotal = _parse_float(subtotal_str)
    tax = _parse_float(tax_str)
    total = _parse_float(total_str)

    line_items: List[LineItem] = []
    item_pattern = re.compile(r"(.+?)\s+([0-9]+\.[0-9]{2})$")
    for line in lines:
        m = item_pattern.search(line)
        if not m:
            continue
        desc, amt_str = m.groups()
        amt = _parse_float(amt_str)
        if amt is not None:
            line_items.append(LineItem(description=desc.strip(), amount=amt))

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
