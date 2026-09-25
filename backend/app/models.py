import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Text, Boolean, Integer, Float, JSON
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Thread(Base):
    """A reconstructed email conversation thread."""
    __tablename__ = "threads"

    id = Column(String, primary_key=True, default=gen_uuid)
    subject_normalized = Column(String, index=True)
    root_message_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    ai_summary = Column(Text, nullable=True)  # Claude-generated thread summary

    emails = relationship("EmailMessage", back_populates="thread", cascade="all, delete-orphan")


class EmailMessage(Base):
    """A single parsed email, with forensic metadata."""
    __tablename__ = "emails"

    id = Column(String, primary_key=True, default=gen_uuid)
    thread_id = Column(String, ForeignKey("threads.id"), nullable=True)

    message_id = Column(String, index=True, nullable=True)
    in_reply_to = Column(String, index=True, nullable=True)
    references = Column(Text, nullable=True)  # space-separated list of message ids

    subject = Column(String, nullable=True)
    sender = Column(String, nullable=True)
    recipients = Column(Text, nullable=True)
    date_sent = Column(String, nullable=True)

    body_preview = Column(Text, nullable=True)
    raw_headers = Column(JSON, nullable=True)

    # Forensic fields
    file_sha256 = Column(String, nullable=True)
    spf_result = Column(String, nullable=True)
    dkim_result = Column(String, nullable=True)
    dmarc_result = Column(String, nullable=True)
    is_spoof_suspected = Column(Boolean, default=False)
    risk_score = Column(Integer, default=0)
    risk_summary = Column(Text, nullable=True)
    ai_risk_narrative = Column(Text, nullable=True)  # Claude-generated investigator narrative

    uploaded_at = Column(DateTime, default=datetime.utcnow)

    thread = relationship("Thread", back_populates="emails")
    hops = relationship("RoutingHop", back_populates="email", cascade="all, delete-orphan")


class RoutingHop(Base):
    """A single hop extracted from a Received: header, geolocated."""
    __tablename__ = "routing_hops"

    id = Column(String, primary_key=True, default=gen_uuid)
    email_id = Column(String, ForeignKey("emails.id"))

    hop_index = Column(Integer)
    ip_address = Column(String, nullable=True)
    hostname = Column(String, nullable=True)
    timestamp_raw = Column(String, nullable=True)

    country = Column(String, nullable=True)
    city = Column(String, nullable=True)
    isp = Column(String, nullable=True)
    asn = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    is_anomalous = Column(Boolean, default=False)
    anomaly_reason = Column(String, nullable=True)

    email = relationship("EmailMessage", back_populates="hops")


class ForensicReport(Base):
    """A generated forensic report for one or more emails/threads."""
    __tablename__ = "forensic_reports"

    id = Column(String, primary_key=True, default=gen_uuid)
    thread_id = Column(String, ForeignKey("threads.id"), nullable=True)
    email_id = Column(String, ForeignKey("emails.id"), nullable=True)

    generated_at = Column(DateTime, default=datetime.utcnow)
    summary = Column(Text, nullable=True)
    risk_score = Column(Integer, default=0)
    findings = Column(JSON, nullable=True)
    evidence_hash = Column(String, nullable=True)
