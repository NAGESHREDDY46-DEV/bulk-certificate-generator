# app/models/certificate.py
# Defines the Certificate database table.
# Each Certificate belongs to exactly one Job (many-to-one relationship).

import enum
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Enum as SAEnum, ForeignKey, Text
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class CertificateStatus(str, enum.Enum):
    """Possible states of an individual certificate."""
    PENDING = "PENDING"       # Not yet generated
    SUCCESS = "SUCCESS"       # PDF created successfully
    FAILED = "FAILED"         # Generation failed (see error_message)


class Certificate(Base):
    """
    SQLAlchemy model for the 'certificates' table.
    Each row represents one certificate for one recipient in a job.
    """
    __tablename__ = "certificates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign key linking this certificate back to its parent Job
    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=False)

    # Recipient details supplied at request time
    recipient_name = Column(String(255), nullable=False)
    recipient_email = Column(String(255), nullable=False)

    # Generation outcome
    status = Column(SAEnum(CertificateStatus, native_enum=False), nullable=False, default=CertificateStatus.PENDING)

    # Path on disk where the PDF was saved (NULL until generated)
    file_path = Column(String(500), nullable=True)

    # If generation failed, store why — helps debugging without digging logs
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationship back to parent Job
    job = relationship("Job", back_populates="certificates")
