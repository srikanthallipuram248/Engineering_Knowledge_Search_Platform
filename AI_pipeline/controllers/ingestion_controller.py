from pathlib import Path
import shutil
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from orchestration.ingestion_pipeline import ingest_pdf
from shared.config import settings

router = APIRouter()


@router.post("/pdf")
async def upload_pdf(
    file: UploadFile = File(...)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )

    filename = f"{uuid.uuid4()}_{file.filename}"

    filepath = Path(settings.UPLOAD_DIR) / filename

    filepath.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(
            file.file,
            buffer
        )

    result = ingest_pdf(str(filepath))

    return result