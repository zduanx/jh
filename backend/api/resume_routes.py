"""
Profile resume API (Phase 7A).

One profile-level resume per user (the resume the chat assistant reasons over),
distinct from the Phase 4C per-tracked-job resume. Mirrors the 4C presigned
direct-to-S3 upload flow (ADR-024), and on confirm: downloads the PDF, extracts
text (pypdf), embeds it (Voyage, ADR-032), and stores everything on the resumes row.

Endpoints (mounted at /api/resume):
- GET  /upload-url   Presigned PUT URL for direct S3 upload
- POST /confirm      Save S3 key + extract text + embed → resumes table
- GET  /url          Presigned GET URL (preview/download)
- GET  /             Resume status for the user
"""

import logging
import os

import boto3
from botocore.config import Config
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from db.session import get_db
from db.jobs_service import search_jobs_by_vector
from models.resume import Resume
from utils.pdf_text import extract_pdf_text
from utils.embeddings import vectorize_text

logger = logging.getLogger(__name__)
router = APIRouter()

RESUME_BUCKET = os.environ.get("RESUME_CONTENT_BUCKET", "")


class UploadUrlResponse(BaseModel):
    upload_url: str
    s3_key: str


class ConfirmRequest(BaseModel):
    s3_key: str
    filename: str


class ResumeStatusResponse(BaseModel):
    has_resume: bool
    filename: str | None = None
    has_embedding: bool = False
    chars: int = 0  # length of extracted text (a quick "did extraction work" signal)


def _s3():
    return boto3.client("s3", config=Config(signature_version="s3v4"))


def _key_for(user_id: int) -> str:
    # One profile resume per user — overwrites on re-upload.
    return f"resumes/{user_id}/profile.pdf"


@router.get("/upload-url", response_model=UploadUrlResponse)
async def get_upload_url(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Presigned PUT URL for direct-to-S3 upload of the profile resume (PDF)."""
    if not RESUME_BUCKET:
        raise HTTPException(status_code=500, detail="Resume storage not configured")
    user_id = current_user["user_id"]
    s3_key = _key_for(user_id)
    upload_url = _s3().generate_presigned_url(
        "put_object",
        Params={"Bucket": RESUME_BUCKET, "Key": s3_key, "ContentType": "application/pdf"},
        ExpiresIn=300,
    )
    return UploadUrlResponse(upload_url=upload_url, s3_key=s3_key)


@router.post("/confirm", response_model=ResumeStatusResponse)
async def confirm_upload(
    request: ConfirmRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    After the client PUTs the PDF to S3: download it, extract text, embed it,
    and upsert the resumes row (one per user).
    """
    if not RESUME_BUCKET:
        raise HTTPException(status_code=500, detail="Resume storage not configured")
    user_id = current_user["user_id"]
    expected_key = _key_for(user_id)
    if request.s3_key != expected_key:
        raise HTTPException(status_code=400, detail="Invalid s3_key for this user")

    # Download the just-uploaded PDF from S3.
    try:
        obj = _s3().get_object(Bucket=RESUME_BUCKET, Key=request.s3_key)
        pdf_bytes = obj["Body"].read()
    except Exception as e:
        logger.exception("resume confirm: S3 download failed")
        raise HTTPException(status_code=400, detail="Uploaded file not found in S3")

    # Extract text from the PDF.
    try:
        text = extract_pdf_text(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Step 3: embed the extracted text (Voyage). Re-upload re-embeds (upsert below).
    try:
        embedding = vectorize_text(text)
    except Exception:
        logger.exception("resume confirm: embedding failed")
        raise HTTPException(status_code=502, detail="Embedding failed (Voyage)")

    # Upsert (one resume per user).
    resume = db.query(Resume).filter(Resume.user_id == user_id).first()
    if resume is None:
        resume = Resume(user_id=user_id)
        db.add(resume)
    resume.s3_url = f"s3://{RESUME_BUCKET}/{request.s3_key}"
    resume.filename = request.filename
    resume.extracted_text = text
    resume.embedding = embedding
    db.commit()

    logger.info(f"resume confirmed for user {user_id}: {len(text)} chars, embedded ({len(embedding)} dim)")
    return ResumeStatusResponse(
        has_resume=True, filename=request.filename, has_embedding=True, chars=len(text)
    )


@router.get("/url")
async def get_download_url(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Presigned GET URL for previewing/downloading the profile resume."""
    if not RESUME_BUCKET:
        raise HTTPException(status_code=500, detail="Resume storage not configured")
    user_id = current_user["user_id"]
    resume = db.query(Resume).filter(Resume.user_id == user_id).first()
    if not resume or not resume.s3_url:
        raise HTTPException(status_code=404, detail="No resume uploaded")
    url = _s3().generate_presigned_url(
        "get_object",
        Params={"Bucket": RESUME_BUCKET, "Key": _key_for(user_id)},
        ExpiresIn=300,
    )
    return {"url": url}


@router.get("/", response_model=ResumeStatusResponse)
async def get_status(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Whether the user has a profile resume + a quick extraction/embedding signal."""
    user_id = current_user["user_id"]
    resume = db.query(Resume).filter(Resume.user_id == user_id).first()
    if not resume:
        return ResumeStatusResponse(has_resume=False)
    return ResumeStatusResponse(
        has_resume=bool(resume.s3_url),
        filename=resume.filename if resume.s3_url else None,
        has_embedding=resume.embedding is not None,
        chars=len(resume.extracted_text or ""),
    )


@router.get("/debug")
async def debug_resume(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Debug/introspection: return the stored extracted text + embedding for the user's
    resume, so we can verify extraction and (Step 3) embedding produced sensible output.
    """
    user_id = current_user["user_id"]
    resume = db.query(Resume).filter(Resume.user_id == user_id).first()
    if not resume:
        # No resume yet — return an empty payload (so the debug view always works).
        return {
            "filename": None,
            "chars": 0,
            "extracted_text": "",
            "embedding_dim": 0,
            "embedding_preview": None,
            "embedding": None,
        }
    # pgvector returns a numpy array (float32) — convert to plain Python floats
    # so FastAPI/JSON can serialize it (numpy types raise a 500 otherwise).
    emb = [float(x) for x in resume.embedding] if resume.embedding is not None else None
    return {
        "filename": resume.filename,
        "chars": len(resume.extracted_text or ""),
        "extracted_text": resume.extracted_text or "",
        "embedding_dim": len(emb) if emb else 0,
        # Full vector can be large (1024 floats) — return a preview + the full array.
        "embedding_preview": emb[:8] if emb else None,
        "embedding": emb,
    }


@router.delete("/")
async def delete_resume(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete the profile resume — removes the S3 object and the DB row.
    S3 delete is immediate and permanent (no versioning/retention on this bucket).
    """
    user_id = current_user["user_id"]
    resume = db.query(Resume).filter(Resume.user_id == user_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="No resume to delete")

    # Delete from S3 (best-effort — proceed to remove the row even if S3 already gone).
    if RESUME_BUCKET and resume.s3_url:
        try:
            _s3().delete_object(Bucket=RESUME_BUCKET, Key=_key_for(user_id))
        except Exception:
            logger.exception("resume delete: S3 delete_object failed (continuing)")

    db.delete(resume)
    db.commit()
    logger.info(f"resume deleted for user {user_id}")
    return {"success": True}


@router.get("/match")
async def match_jobs(
    top_k: int = 10,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Phase 7A (Step 5): semantic match — top-K jobs most similar to the user's
    resume (RAG retrieval, proven in plain code before LLM/MCP). Cosine distance
    via pgvector; smaller distance = closer match.
    """
    user_id = current_user["user_id"]
    resume = db.query(Resume).filter(Resume.user_id == user_id).first()
    if not resume or resume.embedding is None:
        raise HTTPException(status_code=404, detail="No embedded resume — upload one first")

    query_vec = [float(x) for x in resume.embedding]
    results = search_jobs_by_vector(db, user_id, query_vec, top_k=top_k)
    return {
        "top_k": top_k,
        "matches": [
            {
                "job_id": job.id,
                "company": job.company,
                "title": job.title,
                "location": job.location,
                "distance": round(dist, 4),       # cosine distance (0 = identical)
                "similarity": round(1 - dist, 4),  # convenience: higher = closer
            }
            for job, dist in results
        ],
    }
