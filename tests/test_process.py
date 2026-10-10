# tests/test_process.py
# Tests for the Phase 2 endpoints:
#   POST /api/jobs/{job_id}/process   — trigger PDF generation
#   GET  /api/jobs/{job_id}           — poll job status
#   GET  /api/jobs/{job_id}/certificates — list certificates for a job
#   GET  /api/certificates/{id}       — single certificate details
#   GET  /api/certificates/{id}/download — download the PDF file
#
# Covers all assignment requirements:
#   ✔ PDF generation per valid recipient
#   ✔ Job status tracking (PENDING → COMPLETED / COMPLETED_WITH_ERRORS)
#   ✔ Per-certificate SUCCESS / FAILED status with error messages
#   ✔ Continue processing even when one certificate fails
#   ✔ File download — correct response when ready; 409 when not yet generated
#
# All fixtures (client, db_session) come from conftest.py.
# No PostgreSQL or external services needed.

from unittest.mock import patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TWO_RECIPIENTS = [
    {"name": "Alice Smith", "email": "alice@example.com"},
    {"name": "Bob Jones",   "email": "bob@example.com"},
]


def _create_and_process_job(client, recipients=None):
    """
    Helper: POST /api/jobs, then POST /api/jobs/{id}/process.
    Returns (job_id, process_response).
    """
    if recipients is None:
        recipients = TWO_RECIPIENTS

    create = client.post("/api/jobs", json={"recipients": recipients})
    assert create.status_code == 201, create.text
    job_id = create.json()["job_id"]

    process = client.post(f"/api/jobs/{job_id}/process")
    return job_id, process


# ---------------------------------------------------------------------------
# Test 1: Process job — happy path (all certificates succeed)
# ---------------------------------------------------------------------------

def test_process_job_all_success(client):
    """
    POST /api/jobs/{job_id}/process with valid recipients should:
    - Return HTTP 200
    - Set job status to COMPLETED
    - Set successful_count = number of recipients
    - Set failed_count = 0
    """
    job_id, response = _create_and_process_job(client)

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["status"] == "COMPLETED"
    assert data["successful_count"] == 2
    assert data["failed_count"] == 0
    assert data["completed_at"] is not None


# ---------------------------------------------------------------------------
# Test 2: Process job — 404 for unknown job ID
# ---------------------------------------------------------------------------

def test_process_job_not_found(client):
    """
    POST /api/jobs/{unknown_id}/process should return 404.
    """
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.post(f"/api/jobs/{fake_id}/process")
    assert response.status_code == 404, response.text


# ---------------------------------------------------------------------------
# Test 3: Process job — 409 when job is already processed
# ---------------------------------------------------------------------------

def test_process_job_already_processed(client):
    """
    Calling process twice on the same job should return 409 Conflict,
    because the job status is COMPLETED after the first call.
    """
    job_id, first = _create_and_process_job(client)
    assert first.status_code == 200, first.text

    second = client.post(f"/api/jobs/{job_id}/process")
    assert second.status_code == 409, second.text


# ---------------------------------------------------------------------------
# Test 4: GET /api/jobs/{job_id} — status polling
# ---------------------------------------------------------------------------

def test_get_job_status(client):
    """
    GET /api/jobs/{job_id} should return the job's current state.
    After processing, status should be COMPLETED.
    """
    job_id, _ = _create_and_process_job(client)

    response = client.get(f"/api/jobs/{job_id}")
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["id"] == job_id
    assert data["status"] == "COMPLETED"
    assert data["total_recipients"] == 2


# ---------------------------------------------------------------------------
# Test 5: GET /api/jobs/{job_id}/certificates — list all certs for a job
# ---------------------------------------------------------------------------

def test_list_job_certificates(client):
    """
    GET /api/jobs/{job_id}/certificates should return one entry per recipient,
    all with SUCCESS status after processing.
    """
    job_id, _ = _create_and_process_job(client)

    response = client.get(f"/api/jobs/{job_id}/certificates")
    assert response.status_code == 200, response.text
    certs = response.json()

    assert len(certs) == 2
    for cert in certs:
        assert cert["status"] == "SUCCESS"
        assert cert["job_id"] == job_id
        assert cert["file_path"] is not None  # PDF path was recorded


# ---------------------------------------------------------------------------
# Test 6: Individual failure handling
#   One PDF generation fails; the other should still succeed.
#   Job ends with COMPLETED_WITH_ERRORS.
# ---------------------------------------------------------------------------

def test_process_job_one_failure(client):
    """
    When one PDF generation raises an exception:
    - The job continues and processes the remaining recipients.
    - The failed certificate has status FAILED and a non-empty error_message.
    - The successful certificate has status SUCCESS.
    - The job ends with status COMPLETED_WITH_ERRORS.
    """
    # Create a job with 2 recipients
    create = client.post("/api/jobs", json={"recipients": TWO_RECIPIENTS})
    assert create.status_code == 201, create.text
    job_id = create.json()["job_id"]

    # Make the FIRST call to pdf_service raise an error; the second call succeeds.
    call_count = {"n": 0}

    import app.services.pdf_service as pdf_module
    real_fn = pdf_module.generate_certificate

    def mock_generate(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("Simulated PDF generation error")
        return real_fn(*args, **kwargs)

    with patch("app.services.pdf_service.generate_certificate", side_effect=mock_generate):
        response = client.post(f"/api/jobs/{job_id}/process")

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["status"] == "COMPLETED_WITH_ERRORS"
    assert data["successful_count"] == 1
    assert data["failed_count"] == 1

    # Inspect individual certificate statuses
    certs_resp = client.get(f"/api/jobs/{job_id}/certificates")
    certs = certs_resp.json()

    statuses = {c["status"] for c in certs}
    assert "SUCCESS" in statuses
    assert "FAILED" in statuses

    # The failed certificate must have an error message
    failed = next(c for c in certs if c["status"] == "FAILED")
    assert failed["error_message"] is not None
    assert len(failed["error_message"]) > 0


# ---------------------------------------------------------------------------
# Test 7: GET /api/certificates/{id} — single certificate details
# ---------------------------------------------------------------------------

def test_get_single_certificate(client):
    """
    GET /api/certificates/{id} should return full details for one certificate.
    """
    job_id, _ = _create_and_process_job(client)

    # Get the list first to find a valid certificate ID
    certs = client.get(f"/api/jobs/{job_id}/certificates").json()
    cert_id = certs[0]["id"]

    response = client.get(f"/api/certificates/{cert_id}")
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["id"] == cert_id
    assert data["job_id"] == job_id
    assert data["status"] == "SUCCESS"
    assert data["recipient_name"] is not None
    assert data["recipient_email"] is not None


# ---------------------------------------------------------------------------
# Test 8: GET /api/certificates/{id} — 404 for unknown ID
# ---------------------------------------------------------------------------

def test_get_certificate_not_found(client):
    """
    GET /api/certificates/{unknown_id} should return 404.
    """
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/certificates/{fake_id}")
    assert response.status_code == 404, response.text


# ---------------------------------------------------------------------------
# Test 9: Download PDF — 409 when certificate is still PENDING
# ---------------------------------------------------------------------------

def test_download_certificate_pending(client):
    """
    A certificate not yet processed (status=PENDING) cannot be downloaded.
    The endpoint should return 409 Conflict.
    """
    # Create job but DON'T process it
    create = client.post("/api/jobs", json={"recipients": [TWO_RECIPIENTS[0]]})
    job_id = create.json()["job_id"]

    certs = client.get(f"/api/jobs/{job_id}/certificates").json()
    cert_id = certs[0]["id"]

    response = client.get(f"/api/certificates/{cert_id}/download")
    assert response.status_code == 409, response.text


# ---------------------------------------------------------------------------
# Test 10: Download PDF — 200 with PDF content when SUCCESS
# ---------------------------------------------------------------------------

def test_download_certificate_success(client):
    """
    After processing, a SUCCESS certificate can be downloaded.
    The response should have the PDF content type and a non-empty body.
    """
    job_id, _ = _create_and_process_job(client, recipients=[TWO_RECIPIENTS[0]])

    certs = client.get(f"/api/jobs/{job_id}/certificates").json()
    cert_id = certs[0]["id"]

    response = client.get(f"/api/certificates/{cert_id}/download")
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    # PDF files always start with the magic bytes %PDF
    assert response.content[:4] == b"%PDF"
