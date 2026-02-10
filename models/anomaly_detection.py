from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from preprocessing.field_extraction import ExtractedFields


@dataclass
class Anomaly:
    code: str
    message: str
    severity: str


def _check_missing_fields(fields: ExtractedFields) -> List[Anomaly]:
    required = {
        "vendor": fields.vendor,
        "date": fields.date,
        "total": fields.total,
    }
    anomalies: List[Anomaly] = []
    for name, value in required.items():
        if value in (None, "", 0):
            anomalies.append(
                Anomaly(
                    code=f"missing_{name}",
                    message=f"Missing required field: {name}",
                    severity="high",
                )
            )
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
                message=f"Total ({fields.total}) does not match sum of line items ({line_sum:.2f})",
                severity="medium",
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

    if duplicate_detector is not None:
        dup = duplicate_detector.check_duplicate(fields)
        if dup:
            anomalies.append(dup)

    return [asdict(a) for a in anomalies]


__all__ = ["Anomaly", "DuplicateDetector", "detect_anomalies"]
