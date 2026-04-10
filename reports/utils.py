import os

import fitz
import pytesseract
from PIL import Image


pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def _ocr_image(image):
    try:
        return pytesseract.image_to_string(image)
    except Exception:
        return ""


def _ocr_pdf(file_path):
    text_parts = []
    try:
        doc = fitz.open(file_path)
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            text_parts.append(_ocr_image(image))
        doc.close()
    except Exception:
        return ""
    return "\n".join(text_parts).strip()


def extract_text(file_path):
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    if ext == ".pdf":
        try:
            doc = fitz.open(file_path)
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
        except Exception:
            text = ""

        if len(text.strip()) < 50:
            return _ocr_pdf(file_path)
        return text.strip()

    try:
        image = Image.open(file_path)
    except Exception:
        return ""

    return _ocr_image(image).strip()
