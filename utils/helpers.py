from typing import List


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> List[str]:
    if not text:
        return []
    if chunk_size <= overlap:
        overlap = chunk_size // 4

    chunks = []
    start = 0
    text_len = len(text)
    step = chunk_size - overlap
    if step <= 0:
        step = chunk_size // 2

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= text_len:
            break
        start += step

    return chunks


def extract_text_from_file(file_path: str) -> str:
    ext = file_path.lower().rsplit(".", 1)[-1] if "." in file_path else ""
    if ext == "txt":
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    elif ext == "pdf":
        return _extract_pdf_text(file_path)
    elif ext == "docx":
        return _extract_docx_text(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def _extract_pdf_text(file_path: str) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except ImportError:
        raise ImportError("pypdf required for PDF extraction")


def _extract_docx_text(file_path: str) -> str:
    try:
        from docx import Document
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)
    except ImportError:
        raise ImportError("python-docx required for DOCX extraction")


def format_datetime(date_str: str, time_str: str) -> str:
    months = {
        "01": "января", "02": "февраля", "03": "марта",
        "04": "апреля", "05": "мая", "06": "июня",
        "07": "июля", "08": "августа", "09": "сентября",
        "10": "октября", "11": "ноября", "12": "декабря",
    }
    parts = date_str.split("-")
    if len(parts) == 3:
        month = months.get(parts[1], parts[1])
        return f"{int(parts[2])} {month} {parts[0]} в {time_str}"
    return f"{date_str} в {time_str}"


def validate_phone(phone: str) -> bool:
    cleaned = re.sub(r"[\s\-\(\)]", "", phone)
    return bool(re.match(r"^\+?\d{10,15}$", cleaned))


def validate_time(time_str: str) -> bool:
    return bool(re.match(r"^\d{2}:\d{2}$", time_str))
