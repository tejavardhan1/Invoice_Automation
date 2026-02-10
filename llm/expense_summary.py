import os
from typing import Any, Dict, List, Optional

from loguru import logger


def _build_prompt(structured_data: Dict[str, Any], anomalies: List[Dict[str, Any]]) -> str:
    vendor = structured_data.get("vendor")
    total = structured_data.get("total")
    date = structured_data.get("date")
    currency = structured_data.get("currency", "")

    lines = [
        "You are an assistant helping a finance team review invoices and expense receipts.",
        "Summarize the following document in clear business language.",
        "",
        f"Vendor: {vendor}",
        f"Date: {date}",
        f"Total: {total} {currency}".strip(),
        "",
        "Line items:",
    ]
    for item in structured_data.get("line_items", []):
        desc = item.get("description")
        amt = item.get("amount")
        lines.append(f"- {desc}: {amt} {currency}".strip())

    if anomalies:
        lines.append("")
        lines.append("Potential issues detected:")
        for a in anomalies:
            lines.append(f"- ({a.get('severity')}) {a.get('message')}")

    lines.append("")
    lines.append(
        "Produce:\n"
        "1) A 2–3 sentence explanation of the expense.\n"
        "2) Briefly call out any unusual or high-risk charges.\n"
        "3) Keep it under 150 words."
    )
    return "\n".join(lines)


def _fallback_summary(structured_data: Dict[str, Any], anomalies: List[Dict[str, Any]]) -> str:
    vendor = structured_data.get("vendor", "Unknown vendor")
    total = structured_data.get("total", "N/A")
    currency = structured_data.get("currency", "")
    base = f"Invoice/expense from {vendor} with total {total} {currency}."
    if anomalies:
        base += " Potential issues were detected; please review the anomaly list."
    return base


def generate_expense_summary(
    structured_data: Dict[str, Any],
    anomalies: Optional[List[Dict[str, Any]]] = None,
    model: Optional[str] = None,
) -> str:
    anomalies = anomalies or []
    model = model or os.getenv("OLLAMA_MODEL", "llama3.2")
    prompt = _build_prompt(structured_data, anomalies)

    try:
        from ollama import chat

        response = chat(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful financial analyst assistant."},
                {"role": "user", "content": prompt},
            ],
        )
        return (response.message.content or "").strip() or _fallback_summary(structured_data, anomalies)
    except Exception as exc:
        logger.error(f"Failed to generate expense summary via Ollama: {exc}")
        return _fallback_summary(structured_data, anomalies)


__all__ = ["generate_expense_summary"]
