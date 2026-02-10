from typing import Any, Dict, List, Optional

from loguru import logger
from openai import OpenAI


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


def generate_expense_summary(
    structured_data: Dict[str, Any],
    anomalies: Optional[List[Dict[str, Any]]] = None,
    model: str = "gpt-4o-mini",
) -> str:
    anomalies = anomalies or []
    prompt = _build_prompt(structured_data, anomalies)

    try:
        client = OpenAI()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful financial analyst assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip() or ""
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to generate expense summary via LLM: {exc}")
        vendor = structured_data.get("vendor", "Unknown vendor")
        total = structured_data.get("total", "N/A")
        currency = structured_data.get("currency", "")
        base = f"Invoice/expense from {vendor} with total {total} {currency}."
        if anomalies:
            base += " Potential issues were detected; please review the anomaly list."
        return base


__all__ = ["generate_expense_summary"]
