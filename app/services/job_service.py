# app/services/job_service.py
# Business logic for creating a bulk certificate job.
# Keeps the router thin — all DB operations live here.
#
# Responsibilities:
#   1. Create a Job row.
#   2. Create one Certificate row per recipient.
#   3. Wrap everything in a single transaction (commit or rollback atomically).

from typing import List

from sqlalchemy.orm import Session

from app.models.certificate import Certificate, CertificateStatus
from app.models.job import Job, JobStatus
from app.schemas.job import RecipientInput


def create_bulk_job(db: Session, recipients: List[RecipientInput]) -> Job:
    """
    Create a Job and its Certificate records in a single atomic transaction.

    Steps:
    - Insert the Job (PENDING, total_recipients set, counts at 0).
    - Flush to generate the Job's UUID without committing.
    - Insert one Certificate (PENDING) per recipient, linked to the Job.
    - Commit the transaction.
    - Refresh and return the Job ORM object for serialization.

    If anything fails, the transaction is rolled back and the exception
    is re-raised so the router can return an appropriate HTTP 500.
    """
    try:
        # 1. Create the Job record
        job = Job(
            status=JobStatus.PENDING,
            total_recipients=len(recipients),
            successful_count=0,
            failed_count=0,
        )
        db.add(job)

        # flush() sends the INSERT to the DB engine and populates job.id,
        # but does NOT commit — still part of the current transaction.
        db.flush()

        # 2. Create one Certificate per recipient
        certificates = [
            Certificate(
                job_id=job.id,
                recipient_name=recipient.name,
                recipient_email=str(recipient.email),
                status=CertificateStatus.PENDING,
            )
            for recipient in recipients
        ]
        db.add_all(certificates)

        # 3. Commit the whole transaction atomically
        db.commit()

        # Refresh so all DB-generated fields (timestamps, etc.) are loaded
        db.refresh(job)
        return job

    except Exception:
        # Roll back every pending change — no partial records left behind
        db.rollback()
        raise
