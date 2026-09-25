"""
report_generator.py
--------------------
Compiles the parsed/analyzed data for an email (or a whole thread) into a
structured JSON forensic finding, and can render that finding as a
court-style PDF report using fpdf2.
"""

from datetime import datetime, timezone
from fpdf import FPDF

from app.utils.hashing import sha256_bytes


def build_findings(email_row) -> dict:
    """Build the structured JSON findings block for one EmailMessage row."""
    return {
        "message_id": email_row.message_id,
        "subject": email_row.subject,
        "from": email_row.sender,
        "to": email_row.recipients,
        "date_sent": email_row.date_sent,
        "authentication": {
            "spf": email_row.spf_result,
            "dkim": email_row.dkim_result,
            "dmarc": email_row.dmarc_result,
        },
        "risk_score": email_row.risk_score,
        "risk_summary": email_row.risk_summary,
        "ai_risk_narrative": email_row.ai_risk_narrative,
        "is_spoof_suspected": email_row.is_spoof_suspected,
        "routing_hops": [
            {
                "hop_index": h.hop_index,
                "ip_address": h.ip_address,
                "hostname": h.hostname,
                "country": h.country,
                "city": h.city,
                "isp": h.isp,
                "is_anomalous": h.is_anomalous,
                "anomaly_reason": h.anomaly_reason,
            }
            for h in sorted(email_row.hops, key=lambda x: x.hop_index)
        ],
        "evidence_file_sha256": email_row.file_sha256,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def build_evidence_hash(findings: dict) -> str:
    """Hash the findings JSON itself, so the report's integrity can also be verified."""
    import json

    payload = json.dumps(findings, sort_keys=True).encode("utf-8")
    return sha256_bytes(payload)


class ForensicPDF(FPDF):

    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(20, 20, 20)
        self.cell(
            0,
            10,
            "Email Forensic Investigation Report",
            ln=True,
            align="C"
        )

        self.set_font("Helvetica", "", 9)
        self.set_text_color(100, 100, 100)

        generated = datetime.now(timezone.utc).isoformat()
        self.cell(
            0,
            6,
            f"Generated: {generated}",
            ln=True,
            align="C"
        )

        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(
            0,
            10,
            f"Page {self.page_no()}",
            align="C"
        )


def render_pdf(findings: dict, evidence_hash: str) -> bytes:
    pdf = ForensicPDF()
    pdf.add_page()
    pdf.set_text_color(0, 0, 0)

    def section(title):
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(
            0,
            8,
            title,
            ln=True,
            fill=True
        )
        pdf.set_font("Helvetica", "", 10)

    def clean_text(value):
        """
        Convert values to PDF-safe text.
        Helvetica does not support many Unicode characters.
        """
        if value in (None, ""):
            return "-"

        text = str(value)

        replacements = {
            "—": "-",
            "–": "-",
            "-": "-",
            "“": '"',
            "”": '"',
            "‘": "'",
            "’": "'",
            "…": "...",
            "•": "*",
            "→": "->",
            "←": "<-",
            "✓": "[OK]",
            "✗": "[X]",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        # Remove any remaining characters that Helvetica cannot encode.
        text = text.encode("latin-1", errors="replace").decode("latin-1")

        return text

    def row(label, value):
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(45, 7, clean_text(f"{label}:"))

        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(
            135,
            7,
            clean_text(value)
        )

    section("Message Summary")

    row("Message-ID", findings.get("message_id"))
    row("Subject", findings.get("subject"))
    row("From", findings.get("from"))
    row("To", findings.get("to"))
    row("Date Sent", findings.get("date_sent"))

    section("Authentication Results")

    auth = findings.get("authentication", {})

    row("SPF", auth.get("spf"))
    row("DKIM", auth.get("dkim"))
    row("DMARC", auth.get("dmarc"))

    section("Risk Assessment")

    row(
        "Risk Score",
        f"{findings.get('risk_score')}/100"
    )

    row(
        "Spoofing Suspected",
        "YES" if findings.get("is_spoof_suspected") else "No"
    )

    row(
        "Rule-Based Summary",
        findings.get("risk_summary")
    )

    section("AI Investigator Narrative (Claude)")

    pdf.set_font("Helvetica", "I", 10)

    ai_narrative = clean_text(
        findings.get("ai_risk_narrative") or "Not generated."
    )

    pdf.multi_cell(
        180,
        6,
        ai_narrative
    )

    section("Routing Hop Chain")

    for hop in findings.get("routing_hops", []):

        flag = "  [ANOMALY]" if hop.get("is_anomalous") else ""

        line = (
            f"Hop {hop.get('hop_index')}: "
            f"{hop.get('ip_address') or 'unknown IP'} "
            f"({hop.get('city') or '?'}, "
            f"{hop.get('country') or '?'}) "
            f"via {hop.get('hostname') or 'unknown host'}"
            f"{flag}"
        )

        line = clean_text(line)

        pdf.set_font(
            "Helvetica",
            "B" if hop.get("is_anomalous") else "",
            9
        )

        pdf.multi_cell(
            180,
            6,
            line
        )

        if hop.get("anomaly_reason"):

            pdf.set_font(
                "Helvetica",
                "I",
                9
            )

            reason = clean_text(
                f"   Reason: {hop['anomaly_reason']}"
            )

            pdf.multi_cell(
                180,
                6,
                reason
            )

    section("Chain of Custody")

    row(
        "Original File SHA-256",
        findings.get("evidence_file_sha256")
    )

    row(
        "Findings Record SHA-256",
        evidence_hash
    )

    return bytes(pdf.output())