import json
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EmailMessage, ForensicReport
from app.schemas import ReportOut
from app.services.report_generator import build_findings, build_evidence_hash, render_pdf
from app.services.ai_summary import generate_risk_narrative

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("/{email_id}/generate", response_model=ReportOut)
def generate_report(email_id: str, db: Session = Depends(get_db)):
    email_row = db.get(EmailMessage, email_id)
    if not email_row:
        raise HTTPException(status_code=404, detail="Email not found")

    # AI narrative sits on top of the deterministic rule-based findings below —
    # it explains them, it doesn't decide the risk score.
    if not email_row.ai_risk_narrative:
        email_row.ai_risk_narrative = generate_risk_narrative(email_row)
        db.flush()

    findings = build_findings(email_row)
    evidence_hash = build_evidence_hash(findings)

    report = ForensicReport(
        thread_id=email_row.thread_id,
        email_id=email_row.id,
        summary=email_row.risk_summary,
        risk_score=email_row.risk_score,
        findings=findings,
        evidence_hash=evidence_hash,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/{report_id}/download/json")
def download_json(report_id: str, db: Session = Depends(get_db)):
    report = db.get(ForensicReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    payload = json.dumps(report.findings, indent=2)
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="forensic_report_{report_id}.json"'},
    )


@router.get("/{report_id}/download/pdf")
def download_pdf(report_id: str, db: Session = Depends(get_db)):
    report = db.get(ForensicReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    pdf_bytes = render_pdf(report.findings, report.evidence_hash)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="forensic_report_{report_id}.pdf"'},
    )


@router.get("/{report_id}/download/csv")
def download_csv(report_id: str, db: Session = Depends(get_db)):
    report = db.get(ForensicReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    findings = report.findings
    lines = ["hop_index,ip_address,hostname,country,city,is_anomalous,anomaly_reason"]
    for hop in findings.get("routing_hops", []):
        lines.append(",".join([
            str(hop.get("hop_index", "")),
            hop.get("ip_address") or "",
            hop.get("hostname") or "",
            hop.get("country") or "",
            hop.get("city") or "",
            str(hop.get("is_anomalous", False)),
            (hop.get("anomaly_reason") or "").replace(",", ";"),
        ]))
    csv_content = "\n".join(lines)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="evidence_log_{report_id}.csv"'},
    )
