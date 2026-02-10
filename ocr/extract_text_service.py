from pathlib import Path
from typing import Dict, Tuple

from loguru import logger

from .extract_text import extract_text_from_file


def extract_text_from_upload(path: Path) -> Tuple[str, Dict]:
    logger.info(f"Running OCR pipeline for uploaded file: {path}")
    text, meta = extract_text_from_file(str(path))
    meta = {**meta, "size_bytes": path.stat().st_size}
    return text, meta


__all__ = ["extract_text_from_upload"]
