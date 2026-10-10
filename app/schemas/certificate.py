# app/schemas/certificate.py
# Pydantic schemas for Certificate — request input and API responses.
# NOTE: RecipientInput has been moved to schemas/job.py (it belongs to job creation).
# It is re-imported here so any code that imported it from this module continues to work.

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.certificate import CertificateStatus

# Re-export so existing imports like `from app.schemas.certificate import RecipientInput` still work
from app.schemas.job import RecipientInput as RecipientInput  # noqa: F401


class CertificateResponse(BaseModel):
    """
    Schema returned when a client requests certificate information.
    """
    id: uuid.UUID
    job_id: uuid.UUID
    recipient_name: str
    recipient_email: str
    status: CertificateStatus
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
