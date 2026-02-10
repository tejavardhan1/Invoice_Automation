from dataclasses import dataclass
from enum import Enum
from typing import List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression


class DocumentType(str, Enum):
    INVOICE = "invoice"
    EXPENSE_RECEIPT = "expense_receipt"
    OTHER = "other"


@dataclass
class DocumentClassificationResult:
    doc_type: DocumentType
    confidence: float


def _build_rule_based_fallback(text: str) -> DocumentClassificationResult:
    lower = text.lower()
    if "invoice" in lower and ("#" in text or "number" in lower or "date" in lower):
        return DocumentClassificationResult(DocumentType.INVOICE, confidence=0.7)
    if "receipt" in lower or "thank you for your purchase" in lower:
        return DocumentClassificationResult(DocumentType.EXPENSE_RECEIPT, confidence=0.7)
    return DocumentClassificationResult(DocumentType.OTHER, confidence=0.5)


def train_demo_classifier(texts: List[str], labels: List[str]) -> Pipeline:
    clf = Pipeline(
        steps=[
            ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
            ("logreg", LogisticRegression(max_iter=1000)),
        ]
    )
    clf.fit(texts, labels)
    return clf


def classify_document(text: str, model: Pipeline | None = None) -> DocumentClassificationResult:
    if model is None:
        return _build_rule_based_fallback(text)

    proba = model.predict_proba([text])[0]
    labels = model.classes_
    max_idx = proba.argmax()
    predicted_label = labels[max_idx]
    confidence = float(proba[max_idx])

    try:
        doc_type = DocumentType(predicted_label)
    except ValueError:
        doc_type = DocumentType.OTHER

    return DocumentClassificationResult(doc_type=doc_type, confidence=confidence)


__all__ = [
    "DocumentType",
    "DocumentClassificationResult",
    "train_demo_classifier",
    "classify_document",
]
