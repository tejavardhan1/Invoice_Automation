from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from preprocessing.field_extraction import ExtractedFields


@dataclass
class Anomaly:
    code: str
    message: str
    severity: str


def _check_missing_fields(fields: ExtractedFields) -> List[Anomaly]:
    required = [
        ("vendor", fields.vendor, "Vendor name is missing"),
        ("invoice_number", fields.invoice_number, "Invoice number is missing"),
        ("date", fields.date, "Invoice date is missing"),
        ("total", fields.total, "Total amount is missing"),
    ]
    anomalies: List[Anomaly] = []
    for name, value, msg in required:
        if value in (None, "", 0):
            anomalies.append(Anomaly(code=f"missing_{name}", message=msg, severity="high"))
    return anomalies


def _check_total_vs_line_items(fields: ExtractedFields) -> List[Anomaly]:
    anomalies: List[Anomaly] = []
    if fields.total is None or not fields.line_items:
        return anomalies
    line_sum = sum(item.amount for item in fields.line_items)
    if line_sum == 0:
        return anomalies
    diff = abs(line_sum - fields.total)
    if diff > 0.01 * line_sum and diff > 1.0:
        anomalies.append(
            Anomaly(
                code="total_mismatch",
                message=f"Total ({fields.total}) does not match sum of line items ({line_sum:.2f}). Difference: {diff:.2f}.",
                severity="high",
            )
        )
    return anomalies


def _check_subtotal_tax_total(fields: ExtractedFields) -> List[Anomaly]:
    anomalies: List[Anomaly] = []
    if fields.subtotal is None or fields.total is None:
        return anomalies
    if fields.tax is not None:
        expected_total = fields.subtotal + fields.tax
        if abs(expected_total - fields.total) > 0.02 * fields.total and abs(expected_total - fields.total) > 1.0:
            anomalies.append(
                Anomaly(
                    code="subtotal_tax_mismatch",
                    message=f"Subtotal ({fields.subtotal}) + Tax ({fields.tax}) = {expected_total:.2f}, but Total is {fields.total}.",
                    severity="high",
                )
            )
    elif abs(fields.subtotal - fields.total) > 0.02 * fields.total and abs(fields.subtotal - fields.total) > 1.0:
        anomalies.append(
            Anomaly(
                code="subtotal_total_mismatch",
                message=f"Subtotal ({fields.subtotal}) does not match Total ({fields.total}). Tax may be missing or incorrect.",
                severity="medium",
            )
        )
    return anomalies


def _check_date_future(fields: ExtractedFields) -> List[Anomaly]:
    anomalies: List[Anomaly] = []
    if not fields.date:
        return anomalies
    try:
        if isinstance(fields.date, str) and len(fields.date) >= 10:
            d = datetime.strptime(fields.date[:10], "%Y-%m-%d").date()
            if d > datetime.now().date():
                anomalies.append(
                    Anomaly(
                        code="future_date",
                        message=f"Invoice date ({fields.date}) is in the future. Verify correctness.",
                        severity="medium",
                    )
                )
    except ValueError:
        pass
    return anomalies


def _check_negative_amounts(fields: ExtractedFields) -> List[Anomaly]:
    anomalies: List[Anomaly] = []
    if fields.total is not None and fields.total < 0:
        anomalies.append(Anomaly(code="negative_total", message="Total amount is negative (credit/refund). Confirm this is expected.", severity="medium"))
    if fields.tax is not None and fields.tax < 0:
        anomalies.append(Anomaly(code="negative_tax", message="Tax amount is negative. Verify.", severity="high"))
    for item in fields.line_items:
        if item.amount < 0:
            desc = item.description[:40] + ("..." if len(item.description) > 40 else "")
            anomalies.append(
                Anomaly(code="negative_line_item", message=f"Line item '{desc}' has negative amount: {item.amount}.", severity="medium")
            )
    return anomalies


def _check_duplicate_line_items(fields: ExtractedFields) -> List[Anomaly]:
    anomalies: List[Anomaly] = []
    if len(fields.line_items) < 2:
        return anomalies
    seen: Dict[str, float] = {}
    for item in fields.line_items:
        key = (item.description.strip().lower(), round(item.amount, 2))
        k = f"{key[0]}|{key[1]}"
        if k in seen:
            anomalies.append(
                Anomaly(
                    code="duplicate_line_item",
                    message=f"Duplicate line: '{item.description}' with amount {item.amount} appears more than once.",
                    severity="high",
                )
            )
        seen[k] = item.amount
    return anomalies


def _check_empty_line_items_with_total(fields: ExtractedFields) -> List[Anomaly]:
    anomalies: List[Anomaly] = []
    if fields.total is not None and fields.total != 0 and not fields.line_items:
        anomalies.append(
            Anomaly(
                code="no_line_items",
                message="Total amount is present but no line items were extracted. Line items may be missing or in an unsupported format.",
                severity="medium",
            )
        )
    return anomalies


def _check_tax_rate_sanity(fields: ExtractedFields) -> List[Anomaly]:
    anomalies: List[Anomaly] = []
    if fields.subtotal is None or fields.tax is None or fields.subtotal == 0:
        return anomalies
    rate_pct = (fields.tax / fields.subtotal) * 100
    if rate_pct < 0 or rate_pct > 50:
        anomalies.append(
            Anomaly(
                code="unusual_tax_rate",
                message=f"Tax rate appears unusual: {rate_pct:.1f}% (tax {fields.tax} on subtotal {fields.subtotal}). Typical rates are 0–30%.",
                severity="low",
            )
        )
    return anomalies


class DuplicateDetector:
    def __init__(self) -> None:
        self._seen_keys: set[str] = set()

    def _build_key(self, fields: ExtractedFields) -> Optional[str]:
        if not (fields.vendor and fields.invoice_number and fields.total):
            return None
        return f"{fields.vendor}|{fields.invoice_number}|{fields.total}"

    def check_duplicate(self, fields: ExtractedFields) -> Optional[Anomaly]:
        key = self._build_key(fields)
        if key is None:
            return None
        if key in self._seen_keys:
            return Anomaly(
                code="possible_duplicate",
                message="This invoice appears to be a duplicate (same vendor, invoice number, and total).",
                severity="high",
            )
        self._seen_keys.add(key)
        return None


def detect_anomalies(fields: ExtractedFields, duplicate_detector: DuplicateDetector | None = None) -> List[Dict[str, Any]]:
    anomalies: List[Anomaly] = []
    anomalies.extend(_check_missing_fields(fields))
    anomalies.extend(_check_total_vs_line_items(fields))
    anomalies.extend(_check_subtotal_tax_total(fields))
    anomalies.extend(_check_date_future(fields))
    anomalies.extend(_check_negative_amounts(fields))
    anomalies.extend(_check_duplicate_line_items(fields))
    anomalies.extend(_check_empty_line_items_with_total(fields))
    anomalies.extend(_check_tax_rate_sanity(fields))

    if duplicate_detector is not None:
        dup = duplicate_detector.check_duplicate(fields)
        if dup:
            anomalies.append(dup)

    return [asdict(a) for a in anomalies]


__all__ = ["Anomaly", "DuplicateDetector", "detect_anomalies"]
