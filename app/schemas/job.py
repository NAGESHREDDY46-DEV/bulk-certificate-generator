# app/schemas/job.py
# Pydantic schemas for Job — used for API request/response validation and serialization.
# Schemas are separate from SQLAlchemy models: models talk to the DB, schemas talk to the API.

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.models.job import JobStatus


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class RecipientInput(BaseModel):
    """
    A single recipient in a bulk job request.
    Pydantic validates name (non-empty) and email (valid format) automatically.
    """
    name: str
    email: EmailStr

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        """Strip surrounding whitespace and reject an empty/whitespace-only name."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("name must not be empty or blank")
        return stripped


class BulkJobRequest(BaseModel):
    """
    Request body for POST /api/jobs.
    Must contain at least one recipient.
    """
    recipients: List[RecipientInput]

    @field_validator("recipients")
    @classmethod
    def recipients_must_not_be_empty(cls, v: List[RecipientInput]) -> List[RecipientInput]:
        """Reject requests with an empty recipients list."""
        if not v:
            raise ValueError("recipients list must contain at least one recipient")
        return v


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class JobResponse(BaseModel):
    """
    Schema returned when a client requests job information.
    Shows the job's current state and progress counters.
    """
    id: uuid.UUID
    status: JobStatus
    total_recipients: int
    successful_count: int
    failed_count: int
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        # Allows Pydantic to read data from SQLAlchemy model attributes directly
        from_attributes = True


class BulkJobResponse(BaseModel):
    """
    Slim response returned immediately after POST /api/jobs.
    Uses 'job_id' (not 'id') for clarity at the API boundary.
    """
    job_id: uuid.UUID
    status: JobStatus
    total_recipients: int
    successful_count: int
    failed_count: int

    class Config:
        from_attributes = True
