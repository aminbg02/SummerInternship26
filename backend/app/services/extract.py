
import io
import os


class ExtractionError(Exception):
    pass


def _extract_pdf(raw: bytes) -> str:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(raw))
        # extract_text() returns None on image-only pages.
        pages = [(page.extract_text() or "") for page in reader.pages]
    except Exception as e:  # noqa: BLE001
        raise ExtractionError(f"could not read PDF: {e}") from e
    return "\n".join(pages)


def _extract_docx(raw: bytes) -> str:
    import docx  # python-docx

    try:
        document = docx.Document(io.BytesIO(raw))
        paragraphs = [p.text for p in document.paragraphs]
    except Exception as e:  # noqa: BLE001
        raise ExtractionError(f"could not read Word document: {e}") from e
    return "\n".join(paragraphs)


def _extract_txt(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ExtractionError("only UTF-8 text is supported for this file type") from e


_EXTRACTORS = {
    ".pdf": _extract_pdf,
    ".docx": _extract_docx,
    ".txt": _extract_txt,
    ".md": _extract_txt,
}


def extract_text(filename: str, raw: bytes) -> str:

    ext = os.path.splitext(filename or "")[1].lower()
    extractor = _EXTRACTORS.get(ext, _extract_txt)
    return extractor(raw)
