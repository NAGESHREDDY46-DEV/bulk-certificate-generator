# app/services/pdf_service.py
# Generates a single PDF certificate for one recipient using ReportLab.
#
# Why ReportLab?
#   - Pure-Python, no browser/wkhtmltopdf binary required.
#   - Already in requirements.txt (reportlab==4.1.0).
#   - Fine-grained layout control: fonts, colors, borders, images.
#
# Design decision: keep this module stateless.
# It receives the data it needs and returns the saved file path.
# The caller (certificate_service) is responsible for persisting that path.

import os
import uuid
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

# ---------------------------------------------------------------------------
# Output directory — created on first use
# ---------------------------------------------------------------------------
# Resolve relative to the project root (two levels above this file: app/services → app → root)
_PROJECT_ROOT = Path(__file__).parent.parent.parent
OUTPUT_DIR = _PROJECT_ROOT / "generated_certificates"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_certificate(
    recipient_name: str,
    recipient_email: str,
    job_id: str,
    certificate_id: str,
) -> str:
    """
    Generate a single PDF certificate and save it to disk.

    Parameters
    ----------
    recipient_name  : Full name of the award recipient.
    recipient_email : Email (used as a secondary identifier on the certificate).
    job_id          : UUID string of the parent job (used in the output path).
    certificate_id  : UUID string of this certificate (used as filename).

    Returns
    -------
    str
        Absolute path to the saved PDF file.

    Raises
    ------
    Exception
        Re-raises any ReportLab / IO error so the caller can mark the
        certificate as FAILED and store the error_message.
    """
    # Each job gets its own sub-directory so files are easy to browse / zip
    job_dir = OUTPUT_DIR / str(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)

    output_path = job_dir / f"{certificate_id}.pdf"

    _draw_certificate(
        path=str(output_path),
        recipient_name=recipient_name,
        recipient_email=recipient_email,
    )

    return str(output_path)


# ---------------------------------------------------------------------------
# Internal drawing logic
# ---------------------------------------------------------------------------

def _draw_certificate(path: str, recipient_name: str, recipient_email: str) -> None:
    """
    Draw the certificate onto the canvas and save it.

    Layout (landscape A4, 297 mm × 210 mm):
    ┌────────────────────────────────────────────────────────┐
    │  [border]                                               │
    │                                                         │
    │          CERTIFICATE OF COMPLETION                      │
    │                                                         │
    │             This is to certify that                     │
    │                                                         │
    │               << Recipient Name >>                      │
    │                                                         │
    │  has successfully completed the course / program.       │
    │                                                         │
    │  Email: recipient@example.com                           │
    │                                                         │
    │                    [decorative line]                     │
    │                      Authorized Signatory               │
    └────────────────────────────────────────────────────────┘
    """
    page_width, page_height = landscape(A4)
    c = canvas.Canvas(path, pagesize=landscape(A4))

    # ---- Outer border ----
    border_margin = 1.5 * cm
    c.setStrokeColor(colors.HexColor("#1a237e"))   # deep navy
    c.setLineWidth(4)
    c.rect(
        border_margin,
        border_margin,
        page_width - 2 * border_margin,
        page_height - 2 * border_margin,
    )

    # Inner thin border
    c.setLineWidth(1.5)
    inner = 2.0 * cm
    c.rect(
        inner,
        inner,
        page_width - 2 * inner,
        page_height - 2 * inner,
    )

    # ---- Background gradient simulation (two filled rects) ----
    c.setFillColor(colors.HexColor("#f5f5ff"))
    c.rect(0, 0, page_width, page_height, fill=1, stroke=0)
    # Redraw borders over the fill
    c.setStrokeColor(colors.HexColor("#1a237e"))
    c.setLineWidth(4)
    c.rect(border_margin, border_margin,
           page_width - 2 * border_margin, page_height - 2 * border_margin)
    c.setLineWidth(1.5)
    c.rect(inner, inner, page_width - 2 * inner, page_height - 2 * inner)

    # ---- Title ----
    c.setFillColor(colors.HexColor("#1a237e"))
    c.setFont("Helvetica-Bold", 36)
    _centered_text(c, "CERTIFICATE OF COMPLETION", page_width, page_height * 0.82)

    # ---- Subtitle line ----
    c.setFont("Helvetica", 14)
    c.setFillColor(colors.HexColor("#555555"))
    _centered_text(c, "This is to certify that", page_width, page_height * 0.68)

    # ---- Recipient name ----
    c.setFillColor(colors.HexColor("#1a237e"))
    c.setFont("Helvetica-BoldOblique", 30)
    _centered_text(c, recipient_name, page_width, page_height * 0.55)

    # Underline beneath name
    name_width = c.stringWidth(recipient_name, "Helvetica-BoldOblique", 30)
    line_x = (page_width - name_width) / 2
    c.setStrokeColor(colors.HexColor("#1a237e"))
    c.setLineWidth(1)
    c.line(line_x, page_height * 0.52, line_x + name_width, page_height * 0.52)

    # ---- Body text ----
    c.setFont("Helvetica", 13)
    c.setFillColor(colors.HexColor("#333333"))
    _centered_text(
        c,
        "has successfully completed the course and met all requirements.",
        page_width,
        page_height * 0.43,
    )

    # ---- Email ----
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor("#777777"))
    _centered_text(c, f"Email: {recipient_email}", page_width, page_height * 0.35)

    # ---- Decorative divider ----
    divider_y = page_height * 0.22
    c.setStrokeColor(colors.HexColor("#1a237e"))
    c.setLineWidth(1)
    line_start = page_width * 0.30
    line_end = page_width * 0.70
    c.line(line_start, divider_y, line_end, divider_y)

    # ---- Signatory label ----
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor("#333333"))
    _centered_text(c, "Authorized Signatory", page_width, page_height * 0.16)

    # Save the page
    c.showPage()
    c.save()


def _centered_text(c: canvas.Canvas, text: str, page_width: float, y: float) -> None:
    """Helper: draw `text` horizontally centred on the page at height `y`."""
    c.drawCentredString(page_width / 2, y, text)
