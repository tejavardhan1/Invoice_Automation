from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from llm.expense_summary import generate_expense_summary
from mlops.mlflow_tracking import configure_mlflow, log_model_metrics, log_model_params, start_run
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
UPLOAD_DIR = Path("data/uploads")
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def _save_upload(file: UploadFile) -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOAD_DIR / (file.filename or "upload")
    return path


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", tags=["web"])
def index():
    if STATIC_DIR.exists():
        return FileResponse(STATIC_DIR / "index.html")
    return {"message": "API running. Visit /docs for Swagger."}


@app.get("/health", tags=["health"])
def health_check() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/upload", tags=["api"])
async def api_upload(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Upload a document. Returns file path and size."""
    path = _save_upload(file)
    content = await file.read()
    path.write_bytes(content)
    return {"filename": path.name, "path": str(path), "size_bytes": len(content)}


@app.post("/api/extract", tags=["api"])
async def api_extract(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Extract structured fields (invoice number, date, total, vendor) from document."""
    path = _save_upload(file)
    content = await file.read()
    path.write_bytes(content)
    try:
        raw_text, ocr_meta = extract_text_from_upload(path)
        fields = extract_fields_from_text(raw_text)
        return {"raw_text_preview": raw_text[:500], "ocr_meta": ocr_meta, "fields": fields.to_dict()}
    finally:
        path.unlink(missing_ok=True)


@app.post("/api/summary", tags=["api"])
async def api_summary(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Generate LLM business summary of the document."""
    path = _save_upload(file)
    content = await file.read()
    path.write_bytes(content)
    try:
        raw_text, _ = extract_text_from_upload(path)
        fields = extract_fields_from_text(raw_text)
        anomalies = detect_anomalies(fields, duplicate_detector=duplicate_detector)
        summary = generate_expense_summary(fields.to_dict(), anomalies=anomalies)
        return {"summary": summary, "fields": fields.to_dict()}
    finally:
        path.unlink(missing_ok=True)


@app.post("/api/analyze", tags=["api"])
async def api_analyze(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Full pipeline: extract, classify, detect anomalies, generate summary."""
    return await _process_invoice_internal(file)


@app.post("/process-invoice", tags=["invoice"])
async def process_invoice(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Legacy endpoint. Same as /api/analyze."""
    return await _process_invoice_internal(file)


async def _process_invoice_internal(file: UploadFile) -> Dict[str, Any]:
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

        try:
            configure_mlflow(experiment_name="invoice-automation")
            with start_run(run_name=f"process-{file.filename}"):
                log_model_params({"doc_type": classification.doc_type.value})
                log_model_metrics({
                    "classification_confidence": classification.confidence,
                    "anomaly_count": len(anomalies),
                    "total_amount": float(fields.total or 0),
                })
        except Exception:  # noqa: BLE001
            pass

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
