# app/services/certificate_service.py
# Orchestrates the PDF generation for all certificates in a job.
#
# Responsibilities:
#   1. Load all PENDING certificates for a given job from the DB.
#   2. Call pdf_service.generate_certificate() for each one.
#   3. Update each Certificate's status (SUCCESS / FAILED) and file_path.
#   4. Update the parent Job's counters and final status.
#
# Why synchronous (not async/Celery)?
#   Phase 2 keeps things simple. We generate synchronously inside the
#   HTTP request. For real workloads you'd offload to a background task.
#   The code is already structured so the service is easy to call from
#   a Celery task or FastAPI BackgroundTasks in a later phase.

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.certificate import Certificate, CertificateStatus
from app.models.job import Job, JobStatus
from app.services import pdf_service


def process_job(db: Session, job: Job) -> Job:
    """
    Generate PDF certificates for every PENDING certificate in *job*.

    Algorithm
    ---------
    - Set job status → PROCESSING.
    - Iterate over all certificates with PENDING status.
    - For each one, call pdf_service; mark SUCCESS or FAILED.
    - After all certificates, compute the final job status.
    - Commit once at the end.

    Parameters
    ----------
    db  : Active SQLAlchemy session (provided by FastAPI's get_db dependency).
    job : The Job ORM object to process.

    Returns
    -------
    Job
        The refreshed Job object after processing.
    """
    # Mark job as started
    job.status = JobStatus.PROCESSING
    db.add(job)
    db.flush()

    # Fetch all PENDING certificates for this job
    pending_certs: list[Certificate] = (
        db.query(Certificate)
        .filter(
            Certificate.job_id == job.id,
            Certificate.status == CertificateStatus.PENDING,
        )
        .all()
    )

    successful = 0
    failed = 0

    for cert in pending_certs:
        try:
            file_path = pdf_service.generate_certificate(
                recipient_name=cert.recipient_name,
                recipient_email=cert.recipient_email,
                job_id=str(job.id),
                certificate_id=str(cert.id),
            )
            cert.status = CertificateStatus.SUCCESS
            cert.file_path = file_path
            successful += 1
        except Exception as exc:
            cert.status = CertificateStatus.FAILED
            cert.error_message = str(exc)
            failed += 1

        db.add(cert)

    # Update job counters and final status
    job.successful_count = successful
    job.failed_count = failed
    job.completed_at = datetime.utcnow()

    if failed == 0:
        job.status = JobStatus.COMPLETED
    elif successful == 0:
        job.status = JobStatus.FAILED
    else:
        job.status = JobStatus.COMPLETED_WITH_ERRORS

    db.add(job)
    db.commit()
    db.refresh(job)
    return job
