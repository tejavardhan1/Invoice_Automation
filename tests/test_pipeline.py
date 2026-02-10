from models.anomaly_detection import DuplicateDetector, detect_anomalies
from models.doc_classifier import DocumentType, classify_document
from preprocessing.field_extraction import extract_fields_from_text
from llm.expense_summary import generate_expense_summary


def _run_full_pipeline(text: str, duplicate_detector: DuplicateDetector | None = None):
    fields = extract_fields_from_text(text)
    classification = classify_document(text)
    anomalies = detect_anomalies(fields, duplicate_detector=duplicate_detector)
    summary = generate_expense_summary(fields.to_dict(), anomalies)
    return fields, classification, anomalies, summary


def test_invoice_basic():
    text = """
    ACME Corp
    Invoice #INV-1001
    Date: 01/10/2024
    Subtotal: 90.00
    Tax: 10.00
    Total: 100.00

    Consulting services  100.00
    """
    fields, classification, anomalies, summary = _run_full_pipeline(text)

    assert classification.doc_type == DocumentType.INVOICE
    assert fields.vendor == "ACME Corp"
    assert fields.total == 100.0
    assert "invoice" in summary.lower() or "expense" in summary.lower()


def test_receipt_basic():
    text = """
    Coffee Shop
    Receipt
    Date: 02/10/2024
    Total: 5.50

    Latte  5.50
    """
    fields, classification, anomalies, _ = _run_full_pipeline(text)

    assert classification.doc_type in {DocumentType.EXPENSE_RECEIPT, DocumentType.OTHER}
    assert fields.vendor == "Coffee Shop"
    assert fields.total == 5.5


def test_missing_total_anomaly():
    text = """
    Vendor Co
    Invoice #123
    Date: 03/10/2024
    """
    fields, _, anomalies, _ = _run_full_pipeline(text)

    codes = {a["code"] for a in anomalies}
    assert "missing_total" in codes


def test_total_mismatch_anomaly():
    text = """
    Tech Vendor
    Invoice #TV-1
    Date: 04/10/2024
    Subtotal: 50.00
    Tax: 5.00
    Total: 40.00

    Subscription  55.00
    """
    fields, _, anomalies, _ = _run_full_pipeline(text)
    codes = {a["code"] for a in anomalies}
    assert "total_mismatch" in codes


def test_duplicate_detection():
    text = """
    Vendor X
    Invoice #DX-9
    Date: 05/10/2024
    Total: 80.00

    Service  80.00
    """
    dup_detector = DuplicateDetector()
    _, _, anomalies_first, _ = _run_full_pipeline(text, duplicate_detector=dup_detector)
    codes_first = {a["code"] for a in anomalies_first}
    assert "possible_duplicate" not in codes_first

    _, _, anomalies_second, _ = _run_full_pipeline(text, duplicate_detector=dup_detector)
    codes_second = {a["code"] for a in anomalies_second}
    assert "possible_duplicate" in codes_second


def test_other_document_type():
    text = """
    Internal Memo
    This is a company memo about a meeting.
    It is just some random text with no financial data.
    """
    _, classification, anomalies, summary = _run_full_pipeline(text)

    assert classification.doc_type == DocumentType.OTHER
    assert isinstance(anomalies, list)
    assert isinstance(summary, str) and len(summary) > 0
