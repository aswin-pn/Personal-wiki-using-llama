import os
import PyPDF2
import docx
from PIL import Image
import pytesseract

def extract_text(filepath):
    """Extracts text from txt, pdf, docx, and images."""
    ext = os.path.splitext(filepath)[1].lower()
    content = ""
    try:
        if ext == ".txt":
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        elif ext == ".pdf":
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        content += text + "\n"
        elif ext in [".doc", ".docx"]:
            doc = docx.Document(filepath)
            for para in doc.paragraphs:
                content += para.text + "\n"
        elif ext in [".png", ".jpg", ".jpeg"]:
            img = Image.open(filepath)
            content = pytesseract.image_to_string(img)
    except Exception as e:
        print(f"[-] Error extracting {filepath}: {e}")
    return content.strip()
