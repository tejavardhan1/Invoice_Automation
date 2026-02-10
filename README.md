## AI-Powered Invoice & Expense Automation System

Built an AI system that automates invoice and expense processing by extracting financial data, detecting anomalies, and generating summaries via APIs.

### Overview

Companies receive large volumes of:
- Vendor invoices
- Employee expense receipts
- PDF / image-based bills

Manual processing is slow and error-prone. This project automates the core workflow end-to-end:

- **Input**: PDF/image uploads via REST API
- **Processing**:
  - OCR to extract raw text
  - ML-based document classification
  - Rule + ML checks to detect duplicates, missing fields, and amount mismatches
- **AI Layer**:
  - LLM-generated expense summaries
  - Flags unusual charges
- **Output**: Clean JSON responses ready for ERP/accounting tools

### Repository Structure

```text
ai-invoice-expense-automation/
│── data/
│── ocr/
│   └── extract_text.py
│
│── preprocessing/
│   └── field_extraction.py
│
│── models/
│   ├── doc_classifier.py
│   ├── anomaly_detection.py
│
│── llm/
│   └── expense_summary.py
│
│── api/
│   └── main.py
│
│── mlops/
│   └── mlflow_tracking.py
│
│── docker/
│   ├── Dockerfile
```

> Note: The top-level folder here is your current project folder (`Invoice Automation`). You can rename it to `ai-invoice-expense-automation` if you wish.

### Tech Stack

- **Language**: Python
- **API**: FastAPI
- **OCR**: Tesseract (via `pytesseract`) and `pdf2image` for PDFs
- **ML**: Scikit-learn (e.g. Random Forest / XGBoost-style classifiers and anomaly detection)
- **LLM**: OpenAI / compatible chat completion API
- **MLOps**: MLflow
- **Containerization**: Docker

### Features

- **Document ingestion API**
  - Upload invoices/receipts as PDF or image
  - Simple REST interface for integration with other tools

- **OCR & text extraction**
  - Uses Tesseract to extract raw text from supported image formats
  - Uses `pdf2image` to rasterize PDFs before OCR (configurable)

- **Field extraction**
  - Heuristic parsing of key financial fields:
    - Vendor name
    - Invoice/receipt date
    - Subtotal / tax / total amounts
    - Currency when possible

- **Document classification**
  - Classifies documents into types like:
    - `invoice`
    - `expense_receipt`
    - `other`
  - Uses a simple ML-ready interface (Scikit-learn), easily extendable to Random Forest / XGBoost with real training data.

- **Anomaly detection**
  - Flags potential issues such as:
    - Missing critical fields
    - Total vs line-item sum mismatches
    - Possible duplicates (by hashing key fields)

- **LLM summarization**
  - Generates natural-language expense summaries from structured JSON
  - Highlights unusual or high-risk charges

### Getting Started

#### 1. Create and activate a virtual environment

```bash
cd "Invoice Automation"
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

#### 2. Install dependencies

```bash
pip install -r requirements.txt
```

You also need Tesseract OCR installed on your system:

- **macOS (Homebrew)**:

```bash
brew install tesseract poppler
```

#### 3. Environment variables

Create a `.env` file (or export environment variables) with your LLM provider key:

```bash
OPENAI_API_KEY=your_api_key_here
```

#### 4. Run the FastAPI app

```bash
uvicorn api.main:app --reload
```

Then open `http://localhost:8000/docs` to try the API.

### API Endpoints

- **POST** `/process-invoice`
  - **Description**: Upload a PDF/image invoice or receipt and receive extracted fields, classification, anomalies, and AI-generated summary.
  - **Request**: `multipart/form-data` with file field `file`
  - **Response**: JSON:
    - `document_type`
    - `fields` (structured financial data)
    - `anomalies`
    - `summary`

### High-Level Flow

1. **Upload** file via `/process-invoice` (FastAPI).
2. **OCR** extracts raw text (`ocr/extract_text.py`).
3. **Field extraction** parses key financial data (`preprocessing/field_extraction.py`).
4. **Classification** labels doc type (`models/doc_classifier.py`).
5. **Anomaly detection** runs rule/ML-based checks (`models/anomaly_detection.py`).
6. **LLM** generates a summary (`llm/expense_summary.py`).
7. **JSON response** is returned, ready to be consumed by ERP/accounting systems.

### MLOps (MLflow)

The `mlops/mlflow_tracking.py` module provides helper utilities to:

- Set up an MLflow tracking URI
- Log parameters, metrics, and artifacts for:
  - Document classifier experiments
  - Anomaly detection models
  - OCR and end-to-end latency/quality measurements

You can extend these utilities when you start training real models on your own dataset.

### Docker

A sample `Dockerfile` is provided under `docker/` to:

- Build a container image with all dependencies
- Run the FastAPI app with Uvicorn in production-friendly settings

### Resume Entry (Copy-Paste Ready)

**AI Invoice & Expense Automation System | Python, OCR, ML, FastAPI, MLflow**

- Developed an AI system to automate invoice and expense processing by extracting structured financial data from PDFs and images.
- Implemented ML-based document classification and anomaly detection to identify duplicates, missing fields, and inconsistent amounts.
- Integrated LLMs to generate expense summaries and highlight unusual charges for business users.
- Exposed functionality through REST APIs and containerized the application using Docker for scalable deployment.

### Next Steps / Extensions

- Replace heuristic classification with a trained Random Forest/XGBoost model.
- Collect real invoice/receipt data to improve field extraction and anomaly rules.
- Add authentication and role-based access control around the API.
- Integrate with an ERP/accounting sandbox (e.g. Odoo, QuickBooks sandbox, or custom ledger).

