from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from llm.expense_summary import generate_expense_summary
from models.anomaly_detection import DuplicateDetector, detect_anomalies
from models.doc_classifier import classify_document
from ocr.extract_text_service import extract_text_from_upload
from preprocessing.field_extraction import extract_fields_from_text

app = FastAPI(
    title="AI Invoice & Expense Automation API",
    description="Upload invoices/receipts as PDF or images and get structured financial data, anomalies, and AI-generated summaries.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

duplicate_detector = DuplicateDetector()


@app.get("/health", tags=["health"])
def health_check() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/process-invoice", tags=["invoice"])
async def process_invoice(file: UploadFile = File(...)) -> Dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename.")

    logger.info(f"Received file for processing: {file.filename}")

    temp_dir = Path("data/uploads")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / file.filename

    content = await file.read()
    temp_path.write_bytes(content)

    try:
        raw_text, ocr_meta = extract_text_from_upload(temp_path)
        fields = extract_fields_from_text(raw_text)
        structured = fields.to_dict()

        classification = classify_document(raw_text)
        anomalies = detect_anomalies(fields, duplicate_detector=duplicate_detector)
        summary = generate_expense_summary(structured, anomalies=anomalies)

        return {
            "document_type": classification.doc_type.value,
            "classification_confidence": classification.confidence,
            "ocr_meta": ocr_meta,
            "fields": structured,
            "anomalies": anomalies,
            "summary": summary,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Failed to process invoice: {exc}")
        raise HTTPException(status_code=500, detail="Failed to process document") from exc
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            logger.warning(f"Failed to delete temp file: {temp_path}")
