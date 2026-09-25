"""
ai_summary.py
-------------
Calls the Claude API (Anthropic Messages API) to turn the structured,
rule-based findings for an email/thread into a plain-English summary and
risk narrative for investigators.

This sits ON TOP of the deterministic detection engine in auth_check.py —
the risk SCORE and anomaly FLAGS are still produced by explainable,
auditable rules (important for evidence that may end up in a report).
Claude's job here is narrower and specific: explain what those rules found,
in investigator-readable language, and summarize the conversation thread.

If ANTHROPIC_API_KEY is not set, every function degrades to a clearly
labeled fallback string instead of crashing the request — so the rest of
the platform (parsing, geolocation, hashing, export) still works without
an API key configured, e.g. for offline demo environments.
"""
import json
import requests

from app.config import settings

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-4-5"


def _call_claude(system_prompt: str, user_prompt: str, max_tokens: int = 400) -> str | None:
    """Low-level call to the Claude Messages API. Returns None on any failure."""
    if not settings.anthropic_api_key:
        return None

    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }

    try:
        resp = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=15)
        if not resp.ok:
            return None
        data = resp.json()
        parts = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
        return "\n".join(parts).strip() or None
    except (requests.RequestException, ValueError, KeyError):
        return None


def generate_risk_narrative(email_row) -> str:
    """
    Turn the rule-based findings for one email (auth results, risk score,
    anomalous hops) into a short investigator-facing explanation.
    """
    hops_summary = [
        {
            "hop_index": h.hop_index,
            "ip": h.ip_address,
            "location": f"{h.city or '?'}, {h.country or '?'}",
            "anomalous": h.is_anomalous,
            "reason": h.anomaly_reason,
        }
        for h in sorted(email_row.hops, key=lambda x: x.hop_index)
    ]

    findings = {
        "subject": email_row.subject,
        "from": email_row.sender,
        "spf": email_row.spf_result,
        "dkim": email_row.dkim_result,
        "dmarc": email_row.dmarc_result,
        "rule_based_risk_score": email_row.risk_score,
        "rule_based_summary": email_row.risk_summary,
        "routing_hops": hops_summary,
    }

    system_prompt = (
        "You are assisting a cybercrime/forensics investigator. You will be given "
        "structured, rule-based findings about one email (authentication results, "
        "routing hop geolocation, and any anomaly flags already detected by a "
        "deterministic rules engine — you are not detecting anything new yourself). "
        "Write a concise 2-4 sentence plain-English narrative explaining what these "
        "findings mean and why they matter for the investigation. Be factual and "
        "measured — do not invent details not present in the data. Do not use markdown."
    )
    user_prompt = f"Findings:\n{json.dumps(findings, indent=2)}\n\nWrite the investigator narrative."

    result = _call_claude(system_prompt, user_prompt)
    if result:
        return result

    # Fallback: still useful, clearly not AI-generated
    return (
        f"[Rule-based summary — Claude API unavailable] {email_row.risk_summary or 'No anomalies detected.'}"
    )


def generate_thread_summary(thread, emails: list) -> str:
    """Summarize an entire reconstructed thread (all emails) for an investigator."""
    thread_data = {
        "subject": thread.subject_normalized,
        "email_count": len(emails),
        "emails": [
            {
                "from": e.sender,
                "subject": e.subject,
                "date": e.date_sent,
                "risk_score": e.risk_score,
                "spoof_suspected": e.is_spoof_suspected,
                "body_preview": e.body_preview,
            }
            for e in emails
        ],
    }

    system_prompt = (
        "You are assisting a cybercrime/forensics investigator reviewing a "
        "reconstructed email thread. Summarize the conversation and flag which "
        "message(s), if any, look suspicious based on the risk scores and spoofing "
        "flags provided. 3-5 sentences, plain English, no markdown, factual only — "
        "do not invent content not present in the data."
    )
    user_prompt = f"Thread data:\n{json.dumps(thread_data, indent=2)}\n\nWrite the thread summary."

    result = _call_claude(system_prompt, user_prompt, max_tokens=500)
    if result:
        return result

    max_risk = max((e.risk_score for e in emails), default=0)
    return (
        f"[Rule-based summary — Claude API unavailable] Thread '{thread.subject_normalized}' "
        f"contains {len(emails)} email(s). Highest risk score in thread: {max_risk}/100."
    )
