from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models import EmailMessage, Thread, RoutingHop
from app.schemas import EmailOut, UploadResponse
from app.services.email_parser import parse_eml
from app.services.thread_engine import find_thread_key, normalize_subject
from app.services.geo_service import build_hop_chain
from app.services.auth_check import parse_auth_results, check_hop_chronology, score_risk
from app.utils.hashing import sha256_bytes

router = APIRouter(prefix="/api/emails", tags=["emails"])


@router.post("/upload", response_model=UploadResponse)
async def upload_emails(files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    """
    Accepts one or more raw .eml files, parses each, reconstructs threads,
    geolocates the routing hop chain, checks authentication, and scores risk.
    """
    email_ids = []
    thread_ids = set()

    for upload in files:
        raw = await upload.read()
        if not raw:
            continue

        parsed = parse_eml(raw)
        file_hash = sha256_bytes(raw)

        # --- Thread reconstruction ---
        thread_key = find_thread_key(parsed)
        thread = db.execute(
            select(Thread).where(Thread.subject_normalized == thread_key)
        ).scalar_one_or_none()
        if thread is None:
            thread = Thread(
                subject_normalized=thread_key,
                root_message_id=parsed.get("message_id"),
            )
            db.add(thread)
            db.flush()  # get thread.id

        # --- Auth / spoof analysis ---
        auth_results = parse_auth_results(parsed.get("authentication_results", []))
        hops_data = build_hop_chain(parsed.get("received_chain", []))
        hops_data = check_hop_chronology(hops_data)
        has_received = len(parsed.get("received_chain", [])) > 0
        risk_score, risk_summary, is_spoof = score_risk(auth_results, hops_data, has_received)

        email_row = EmailMessage(
            thread_id=thread.id,
            message_id=parsed.get("message_id"),
            in_reply_to=parsed.get("in_reply_to"),
            references=" ".join(parsed.get("references", [])),
            subject=parsed.get("subject"),
            sender=parsed.get("sender"),
            recipients=parsed.get("recipients"),
            date_sent=parsed.get("date_sent"),
            body_preview=parsed.get("body_preview"),
            raw_headers=parsed.get("raw_headers"),
            file_sha256=file_hash,
            spf_result=auth_results.get("spf"),
            dkim_result=auth_results.get("dkim"),
            dmarc_result=auth_results.get("dmarc"),
            is_spoof_suspected=is_spoof,
            risk_score=risk_score,
            risk_summary=risk_summary,
        )
        db.add(email_row)
        db.flush()

        for hop in hops_data:
            db.add(RoutingHop(email_id=email_row.id, **hop))

        email_ids.append(email_row.id)
        thread_ids.add(thread.id)

    db.commit()
    return UploadResponse(uploaded=len(email_ids), email_ids=email_ids, thread_ids=list(thread_ids))


@router.get("/{email_id}", response_model=EmailOut)
def get_email(email_id: str, db: Session = Depends(get_db)):
    email_row = db.get(EmailMessage, email_id)
    if not email_row:
        raise HTTPException(status_code=404, detail="Email not found")
    return email_row
