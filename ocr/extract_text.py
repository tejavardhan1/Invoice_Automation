from pathlib import Path
from typing import List, Tuple

import pytesseract
from loguru import logger
from pdf2image import convert_from_path
from PIL import Image


def _ocr_image(image: Image.Image) -> str:
    return pytesseract.image_to_string(image)


def _is_pdf(path: Path) -> bool:
    return path.suffix.lower() == ".pdf"


def _is_image(path: Path) -> bool:
    return path.suffix.lower() in {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}


def _pdf_to_images(pdf_path: Path, dpi: int = 300) -> List[Image.Image]:
    logger.info(f"Converting PDF to images: {pdf_path}")
    return convert_from_path(str(pdf_path), dpi=dpi)


def extract_text_from_file(path: str) -> Tuple[str, dict]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if _is_pdf(file_path):
        images = _pdf_to_images(file_path)
    elif _is_image(file_path):
        logger.info(f"Loading image for OCR: {file_path}")
        images = [Image.open(str(file_path))]
    else:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")

    texts: List[str] = []
    for idx, img in enumerate(images):
        logger.info(f"Running OCR on page/image {idx + 1}/{len(images)}")
        texts.append(_ocr_image(img))

    return "\n".join(texts), {
        "num_pages": len(images),
        "file_type": "pdf" if _is_pdf(file_path) else "image",
        "file_name": file_path.name,
    }


__all__ = ["extract_text_from_file"]
