# app/routers/jobs.py
# HTTP layer for all /api/jobs endpoints.
# Thin layer: parse request → call service → return response.
# All business logic and DB operations live in app/services/.

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.job import Job
from app.schemas.certificate import CertificateResponse
from app.schemas.job import BulkJobRequest, BulkJobResponse, JobResponse
from app.services import certificate_service, job_service

router = APIRouter()


# ---------------------------------------------------------------------------
# POST /api/jobs  —  Create a new bulk job
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=BulkJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a bulk certificate job",
    description=(
        "Submit a list of recipients. The API creates one Job record and one "
        "Certificate record (initially PENDING) per recipient. "
        "Call **POST /api/jobs/{job_id}/process** next to generate the PDFs."
    ),
)
def create_bulk_job(
    request: BulkJobRequest,
    db: Session = Depends(get_db),
) -> BulkJobResponse:
    """
    1. Validate request body (Pydantic — returns 422 on bad data).
    2. Atomically insert Job + Certificates (rolls back on error).
    3. Return slim response with job_id and initial counters.
    """
    try:
        job = job_service.create_bulk_job(db=db, recipients=request.recipients)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create job: {exc}",
        )

    return BulkJobResponse(
        job_id=job.id,
        status=job.status,
        total_recipients=job.total_recipients,
        successful_count=job.successful_count,
        failed_count=job.failed_count,
    )


# ---------------------------------------------------------------------------
# POST /api/jobs/{job_id}/process  —  Trigger PDF generation
# ---------------------------------------------------------------------------

@router.post(
    "/{job_id}/process",
    response_model=JobResponse,
    summary="Process a job — generate all PDFs",
    description=(
        "Triggers synchronous PDF generation for every PENDING certificate "
        "in the job. Returns the Job with updated status and counters once "
        "all certificates have been processed."
    ),
)
def process_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> JobResponse:
    """
    POST /api/jobs/{job_id}/process

    Looks up the job, validates it is in a processable state (PENDING),
    then calls certificate_service.process_job() which generates each PDF,
    updates certificate statuses, and sets the final job status.
    """
    job = _get_job_or_404(db, job_id)

    if job.status not in ("PENDING",):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Job is already in status '{job.status}'. "
                "Only PENDING jobs can be processed."
            ),
        )

    try:
        job = certificate_service.process_job(db=db, job=job)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF generation failed: {exc}",
        )

    return job


# ---------------------------------------------------------------------------
# GET /api/jobs/{job_id}  —  Poll job status
# ---------------------------------------------------------------------------

@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job status",
    description="Returns the current status and progress counters for a job.",
)
def get_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> JobResponse:
    """GET /api/jobs/{job_id} — returns the Job row as JSON."""
    return _get_job_or_404(db, job_id)


# ---------------------------------------------------------------------------
# GET /api/jobs/{job_id}/certificates  —  List certificates for a job
# ---------------------------------------------------------------------------

@router.get(
    "/{job_id}/certificates",
    response_model=List[CertificateResponse],
    summary="List certificates for a job",
    description=(
        "Returns all Certificate records belonging to the given job. "
        "Each entry shows the recipient, generation status, and (if successful) "
        "whether a PDF is available for download."
    ),
)
def list_job_certificates(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> List[CertificateResponse]:
    """GET /api/jobs/{job_id}/certificates"""
    job = _get_job_or_404(db, job_id)
    return job.certificates


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _get_job_or_404(db: Session, job_id: uuid.UUID) -> Job:
    """Fetch a Job by primary key or raise HTTP 404."""
    job = db.query(Job).filter(Job.id == str(job_id)).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )
    return job
