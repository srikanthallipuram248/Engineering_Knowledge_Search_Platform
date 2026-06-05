import uuid
from pathlib import Path

from extraction.pdf_extractor import extract_pdf_pages
from processing.text_chunker import chunk_text
from embeddings.embedding_generator import generate_embeddings
from indexing.index_manager import store_embeddings


def ingest_pdf(file_path: str):
    """
    Full PDF ingestion pipeline.

    PDF
      ↓
    Extract Pages
      ↓
    Chunk Pages
      ↓
    Generate Embeddings
      ↓
    Store in Qdrant
    """

    pages = extract_pdf_pages(file_path)

    texts = []
    ids = []
    payloads = []

    filename = Path(file_path).name

    for page_data in pages:

        page_number = page_data["page"]
        page_text = page_data["text"]

        chunks = chunk_text(page_text)

        for chunk_index, chunk in enumerate(chunks):

            chunk_id = str(uuid.uuid4())

            ids.append(chunk_id)

            texts.append(chunk)

            payloads.append({
                "source": filename,
                "page": page_number,
                "chunk_index": chunk_index,
                "text": chunk
            })

    if not texts:
        return {
            "document": filename,
            "pages": len(pages),
            "chunks": 0,
        }

    embeddings = generate_embeddings(texts)

    store_embeddings(
        ids=ids,
        embeddings=embeddings,
        payloads=payloads
    )

    return {
        "document": filename,
        "pages": len(pages),
        "chunks": len(texts)
    }
