import fitz


def extract_pdf_pages(file_path: str) -> list[dict]:
    """
    Extract text page-by-page.

    Returns:
    [
        {
            "page": 1,
            "text": "..."
        }
    ]
    """

    document = fitz.open(file_path)

    pages = []

    try:
        for page_number, page in enumerate(document, start=1):

            text = page.get_text().strip()

            if text:
                pages.append({
                    "page": page_number,
                    "text": text
                })

    finally:
        document.close()

    return pages
