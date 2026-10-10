# app/routers/certificates.py
# HTTP layer for /api/certificates endpoints.
# Thin layer: parse request → call service/query → return response.

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.certificate import Certificate, CertificateStatus
from app.schemas.certificate import CertificateResponse

# All routes are prefixed with /api/certificates (set in main.py)
router = APIRouter()


# ---------------------------------------------------------------------------
# GET /api/certificates/{id}  —  Single certificate details
# ---------------------------------------------------------------------------

@router.get(
    "/{certificate_id}",
    response_model=CertificateResponse,
    summary="Get certificate details",
    description=(
        "Returns the details of a single certificate including its status, "
        "recipient info, and whether a PDF has been generated."
    ),
)
def get_certificate(
    certificate_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> CertificateResponse:
    """GET /api/certificates/{certificate_id}"""
    cert = _get_cert_or_404(db, certificate_id)
    return cert


# ---------------------------------------------------------------------------
# GET /api/certificates/{id}/download  —  Download the PDF
# ---------------------------------------------------------------------------

@router.get(
    "/{certificate_id}/download",
    summary="Download certificate PDF",
    description=(
        "Streams the generated PDF file for a certificate. "
        "Returns 404 if the certificate doesn't exist, "
        "409 if the PDF has not been generated yet (status != SUCCESS), "
        "and 500 if the file is missing on disk."
    ),
)
def download_certificate(
    certificate_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    GET /api/certificates/{certificate_id}/download

    Uses FastAPI's FileResponse to stream the PDF with correct headers
    so the browser triggers a file download.
    """
    cert = _get_cert_or_404(db, certificate_id)

    # Guard: only SUCCESS certificates have a PDF
    if cert.status != CertificateStatus.SUCCESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"PDF not available. Certificate status is '{cert.status}'. "
                "Process the parent job first."
            ),
        )

    # Guard: file should be on disk — handle edge-cases gracefully
    if not cert.file_path or not os.path.exists(cert.file_path):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF file not found on disk. The record may be stale.",
        )

    # Friendly filename: <recipient_name>_certificate.pdf
    safe_name = cert.recipient_name.replace(" ", "_").replace("/", "-")
    filename = f"{safe_name}_certificate.pdf"

    return FileResponse(
        path=cert.file_path,
        media_type="application/pdf",
        filename=filename,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _get_cert_or_404(db: Session, certificate_id: uuid.UUID) -> Certificate:
    """Fetch a Certificate by primary key or raise HTTP 404."""
    cert = db.query(Certificate).filter(Certificate.id == str(certificate_id)).first()
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate '{certificate_id}' not found.",
        )
    return cert
