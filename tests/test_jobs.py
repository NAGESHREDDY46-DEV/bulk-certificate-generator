# tests/test_jobs.py
# Tests for POST /api/jobs — bulk certificate job creation and input validation.
# All fixtures come from conftest.py (in-memory SQLite, no PostgreSQL needed).
#
# To run:
#   venv\Scripts\pytest tests/test_jobs.py -v

from app.models.certificate import Certificate
from app.models.job import Job

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

VALID_RECIPIENTS = [
    {"name": "Deepika", "email": "deepika@example.com"},
    {"name": "Rahul",   "email": "rahul@example.com"},
    {"name": "Priya",   "email": "priya@example.com"},
]


# ---------------------------------------------------------------------------
# Test 1: Valid bulk job creation
# ---------------------------------------------------------------------------

def test_create_bulk_job_valid(client):
    """
    POST /api/jobs with valid recipients should return HTTP 201
    and the correct response shape.
    """
    response = client.post("/api/jobs", json={"recipients": VALID_RECIPIENTS})

    assert response.status_code == 201, response.text
    data = response.json()

    assert "job_id" in data
    assert data["status"] == "PENDING"
    assert data["total_recipients"] == 3
    assert data["successful_count"] == 0
    assert data["failed_count"] == 0


# ---------------------------------------------------------------------------
# Test 2: Empty recipients list → 422 Unprocessable Entity
# ---------------------------------------------------------------------------

def test_create_bulk_job_empty_recipients(client):
    """
    POST /api/jobs with an empty recipients list should return HTTP 422.
    Pydantic's @field_validator on 'recipients' rejects empty lists.
    """
    response = client.post("/api/jobs", json={"recipients": []})
    assert response.status_code == 422, response.text


# ---------------------------------------------------------------------------
# Test 3: Recipient missing 'name' field → 422
# ---------------------------------------------------------------------------

def test_create_bulk_job_missing_name(client):
    """
    A recipient without a 'name' field fails Pydantic validation (422).
    """
    response = client.post("/api/jobs", json={
        "recipients": [{"email": "no_name@example.com"}]
    })
    assert response.status_code == 422, response.text


# ---------------------------------------------------------------------------
# Test 4: Invalid email format → 422
# ---------------------------------------------------------------------------

def test_create_bulk_job_invalid_email(client):
    """
    A recipient with a badly formatted email fails Pydantic validation (422).
    """
    response = client.post("/api/jobs", json={
        "recipients": [{"name": "Bad Email", "email": "not-an-email"}]
    })
    assert response.status_code == 422, response.text


# ---------------------------------------------------------------------------
# Test 5: Blank name (whitespace only) → 422
# ---------------------------------------------------------------------------

def test_create_bulk_job_blank_name(client):
    """
    A recipient whose name is only spaces is rejected by the name validator.
    """
    response = client.post("/api/jobs", json={
        "recipients": [{"name": "   ", "email": "blank@example.com"}]
    })
    assert response.status_code == 422, response.text


# ---------------------------------------------------------------------------
# Test 6: DB records — Job and Certificate rows are created correctly
# ---------------------------------------------------------------------------

def test_create_bulk_job_records_in_db(client, db_session):
    """
    After a successful POST /api/jobs, verify that:
    - One Job row exists with the correct total_recipients.
    - One Certificate row per recipient exists, all linked to the Job.
    - All certificates start with PENDING status.
    """
    response = client.post("/api/jobs", json={"recipients": VALID_RECIPIENTS})
    assert response.status_code == 201, response.text

    job_id = response.json()["job_id"]  # str UUID from JSON response

    # Verify Job row (id stored as String, so string comparison works directly)
    job = db_session.query(Job).filter(Job.id == job_id).first()
    assert job is not None
    assert job.total_recipients == 3

    # Verify Certificate rows
    certs = db_session.query(Certificate).filter(Certificate.job_id == job_id).all()
    assert len(certs) == 3

    emails = {c.recipient_email for c in certs}
    assert "deepika@example.com" in emails
    assert "rahul@example.com" in emails
    assert "priya@example.com" in emails

    # All certificates should start as PENDING
    for cert in certs:
        assert cert.status.value == "PENDING"
