# app/models/job.py
# Defines the Job database table using SQLAlchemy ORM.
# A Job represents one bulk certificate generation request.

import enum
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class JobStatus(str, enum.Enum):
    """
    Possible states of a certificate generation job.
    Using str makes it easy to compare and serialize values.
    """
    PENDING = "PENDING"               # Job received, not started yet
    PROCESSING = "PROCESSING"         # Job is actively generating certificates
    COMPLETED = "COMPLETED"           # All certificates generated successfully
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"  # Some failed, some succeeded
    FAILED = "FAILED"                 # Entire job failed (e.g., bad input)


class Job(Base):
    """
    SQLAlchemy model for the 'jobs' table.
    Each row represents one bulk generation request.
    """
    __tablename__ = "jobs"

    # UUID primary key — better than integer IDs for APIs (no enumeration risk)
    # Stored as a 36-character string (e.g. "550e8400-e29b-41d4-a716-446655440000").
    # Works with SQLite, PostgreSQL, and any other backend.
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Current state of the job
    # native_enum=False stores the value as VARCHAR instead of a DB-level ENUM type.
    # This is required for SQLite compatibility.
    status = Column(SAEnum(JobStatus, native_enum=False), nullable=False, default=JobStatus.PENDING)

    # How many recipients were submitted
    total_recipients = Column(Integer, nullable=False, default=0)

    # Counters updated as certificates are generated
    successful_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)  # Set when job finishes

    # Relationship: one Job → many Certificates
    # back_populates links to Certificate.job
    certificates = relationship("Certificate", back_populates="job")
