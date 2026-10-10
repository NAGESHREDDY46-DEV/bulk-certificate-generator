# Bulk Certificate Generator API

A clean, readable, and fully functional API to generate PDF certificates in bulk. Designed with simplicity in mind, it uses SQLite and synchronous processing, making it ideal for local testing, assignments, and quick deployments without the overhead of Docker or Celery.

## Features
- **Bulk Job Creation:** Submit a list of recipients to start a PDF generation job.
- **Job Tracking:** Poll the job status (`PENDING`, `PROCESSING`, `COMPLETED`, `COMPLETED_WITH_ERRORS`).
- **Certificate Status:** Track individual certificate statuses (`PENDING`, `SUCCESS`, `FAILED`).
- **PDF Generation:** Powered by `reportlab`. Fault-tolerant (one failure doesn't crash the job).
- **PDF Download:** Download the generated PDF right from the API endpoint.

## Project Structure
- `app/main.py`: FastAPI entrypoint and setup.
- `app/database.py`: SQLAlchemy setup connected to SQLite.
- `app/routers/`: HTTP endpoints (`jobs` and `certificates`).
- `app/services/`: Core logic (`job_service`, `certificate_service`, `pdf_service`).
- `app/models/`: SQLAlchemy ORM models.
- `tests/`: Comprehensive test suite using `pytest`.

## Local Setup

### Prerequisites
- Python 3.10+

### Installation

1. **Clone the repository and enter the directory:**
   ```bash
   git clone <repo-url>
   cd Bulk-Certificate-Generator
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # macOS / Linux
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   Copy the example config:
   ```bash
   # Windows
   copy .env.example .env
   
   # macOS / Linux
   cp .env.example .env
   ```
   *The default `.env` is configured to use SQLite `.db` file out of the box.*

5. **Run the server:**
   ```bash
   uvicorn app.main:app --reload
   ```

6. **View the API Docs:**
   Open your browser to: [http://localhost:8000/docs](http://localhost:8000/docs)

## Running Tests
This project includes a robust test suite that uses an isolated, in-memory SQLite database to ensure the tests run fast and never affect your local development database.

```bash
pytest
```

## Deployment (Free Hosting on Render)

This project can be easily deployed for free on [Render](https://render.com/). Given the simplified SQLite architecture, no external database or worker services are required!

1. Create a new **Web Service** on Render and connect your GitHub repository.
2. In the deployment settings, configure the following:
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Add the following Environment Variables in the Render Dashboard:
   - `DATABASE_URL` = `sqlite:///./bulk_cert.db` (or leave default, as Render will pick it up if you push your `.env` which isn't recommended, but it's best to set it explicitly)
4. Deploy!

> **Note on Render Free Tier:** Render's free instances spin down after inactivity and have an ephemeral file system. Any generated `.db` file and `generated_certificates/` PDF files will be wiped upon restarting or redeploying the app. For production usage, a persistent database (PostgreSQL) and object storage (AWS S3) should be integrated.
