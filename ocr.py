import pytesseract
from pdf2image import convert_from_path

def ocr_pdf(pdf_path):
    """
    Converts each page of the PDF to an image and runs local OCR on it.
    Returns the combined extracted text.
    """
    text = ""

    pages = convert_from_path(pdf_path)

    for page_image in pages:
        page_text = pytesseract.image_to_string(page_image)
        text += page_text + "\n"

    return text