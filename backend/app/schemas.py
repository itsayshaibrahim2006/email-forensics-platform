from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel


class RoutingHopOut(BaseModel):
    hop_index: int
    ip_address: Optional[str] = None
    hostname: Optional[str] = None
    timestamp_raw: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    isp: Optional[str] = None
    asn: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_anomalous: bool = False
    anomaly_reason: Optional[str] = None

    class Config:
        from_attributes = True


class EmailOut(BaseModel):
    id: str
    thread_id: Optional[str] = None
    message_id: Optional[str] = None
    in_reply_to: Optional[str] = None
    subject: Optional[str] = None
    sender: Optional[str] = None
    recipients: Optional[str] = None
    date_sent: Optional[str] = None
    body_preview: Optional[str] = None
    file_sha256: Optional[str] = None
    spf_result: Optional[str] = None
    dkim_result: Optional[str] = None
    dmarc_result: Optional[str] = None
    is_spoof_suspected: bool = False
    risk_score: int = 0
    risk_summary: Optional[str] = None
    ai_risk_narrative: Optional[str] = None
    uploaded_at: datetime
    hops: List[RoutingHopOut] = []

    class Config:
        from_attributes = True


class ThreadOut(BaseModel):
    id: str
    subject_normalized: Optional[str] = None
    root_message_id: Optional[str] = None
    created_at: datetime
    ai_summary: Optional[str] = None
    emails: List[EmailOut] = []

    class Config:
        from_attributes = True


class ThreadSummaryResponse(BaseModel):
    thread_id: str
    ai_summary: str


class ThreadSummaryOut(BaseModel):
    id: str
    subject_normalized: Optional[str] = None
    email_count: int
    max_risk_score: int
    created_at: datetime

    class Config:
        from_attributes = True


class ReportOut(BaseModel):
    id: str
    thread_id: Optional[str] = None
    email_id: Optional[str] = None
    generated_at: datetime
    summary: Optional[str] = None
    risk_score: int
    findings: Optional[Any] = None
    evidence_hash: Optional[str] = None

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    uploaded: int
    email_ids: List[str]
    thread_ids: List[str]
