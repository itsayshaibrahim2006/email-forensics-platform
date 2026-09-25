from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models import Thread, EmailMessage
from app.schemas import ThreadOut, ThreadSummaryOut, ThreadSummaryResponse
from app.services.ai_summary import generate_thread_summary

router = APIRouter(prefix="/api/threads", tags=["threads"])


@router.get("", response_model=list[ThreadSummaryOut])
def list_threads(db: Session = Depends(get_db)):
    threads = db.execute(select(Thread)).scalars().all()
    summaries = []
    for t in threads:
        max_risk = max((e.risk_score for e in t.emails), default=0)
        summaries.append(ThreadSummaryOut(
            id=t.id,
            subject_normalized=t.subject_normalized,
            email_count=len(t.emails),
            max_risk_score=max_risk,
            created_at=t.created_at,
        ))
    # Highest-risk threads first — investigators triage those first
    summaries.sort(key=lambda s: s.max_risk_score, reverse=True)
    return summaries


@router.get("/{thread_id}", response_model=ThreadOut)
def get_thread(thread_id: str, db: Session = Depends(get_db)):
    thread = db.get(Thread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    # Order emails chronologically within the thread for a readable timeline
    thread.emails.sort(key=lambda e: e.uploaded_at)
    return thread


@router.post("/{thread_id}/summarize", response_model=ThreadSummaryResponse)
def summarize_thread(thread_id: str, db: Session = Depends(get_db)):
    """
    Generate (or return the cached) Claude-written summary of the whole
    reconstructed thread — which messages look suspicious and why.
    """
    thread = db.get(Thread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    if not thread.ai_summary:
        thread.ai_summary = generate_thread_summary(thread, thread.emails)
        db.commit()
        db.refresh(thread)

    return ThreadSummaryResponse(thread_id=thread.id, ai_summary=thread.ai_summary)
