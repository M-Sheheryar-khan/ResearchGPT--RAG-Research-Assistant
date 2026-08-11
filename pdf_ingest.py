from pypdf import PdfReader
from ocr import ocr_pdf

MIN_TEXT_LENGTH = 200

def extract_text(pdf_path):
    reader = PdfReader(pdf_path)

    text = ""

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    used_ocr = False

    if len(text.strip()) < MIN_TEXT_LENGTH:
        text = ocr_pdf(pdf_path)
        used_ocr = True

    return text, used_ocr

def extract_metadata(pdf_path):
    reader = PdfReader(pdf_path)
    meta = reader.metadata or {}

    author = meta.get("/Author") or "Unknown"

    year = "Unknown"
    raw_date = meta.get("/CreationDate")
    if raw_date:
        digits = "".join(c for c in raw_date if c.isdigit())
        if len(digits) >= 4:
            year = digits[:4]

    return {
        "author": author,
        "year": year
    }

def chunk_text(text, size=500, overlap=100):
    words = text.split()

    chunks = []

    step = size - overlap

    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + size])
        chunks.append(chunk)

        if i + size >= len(words):
            break

    return chunks