"""
auth_check.py
-------------
Extracts SPF/DKIM/DMARC verdicts from the Authentication-Results header and
runs lightweight heuristics to flag likely header tampering / spoofing:

  1. Auth failures (SPF/DKIM/DMARC = fail or none)
  2. Hop timestamps that run backwards (a hop claiming to happen before the
     hop before it — a classic sign of a manually inserted/forged header)
  3. Missing routing hops entirely (no Received: headers at all)

This is intentionally rule-based and explainable (not a black box) so an
investigator can see exactly why an email was flagged — important for
evidence that may end up in a report.
"""
import re
from datetime import datetime
from email.utils import parsedate_to_datetime

AUTH_RESULT_REGEX = re.compile(r"(spf|dkim|dmarc)\s*=\s*(\w+)", re.IGNORECASE)


def parse_auth_results(auth_headers: list[str]) -> dict:
    """Merge all Authentication-Results headers and pull out spf/dkim/dmarc verdicts."""
    combined = " ".join(auth_headers)
    results = {"spf": None, "dkim": None, "dmarc": None}
    for match in AUTH_RESULT_REGEX.finditer(combined):
        key, value = match.group(1).lower(), match.group(2).lower()
        results[key] = value
    return results


def check_hop_chronology(hops: list[dict]) -> list[dict]:
    """
    Mark hops as anomalous if their timestamp precedes the previous hop's
    timestamp (headers are expected to move forward in time, origin -> dest).
    Mutates and returns the hop dict list, adding is_anomalous/anomaly_reason.
    """
    last_ts = None
    for hop in hops:
        ts = _try_parse_date(hop.get("timestamp_raw"))
        if ts and last_ts and ts < last_ts:
            hop["is_anomalous"] = True
            hop["anomaly_reason"] = "Hop timestamp precedes the prior hop — possible forged/reordered header"
        if ts:
            last_ts = ts
        if not hop.get("ip_address"):
            hop["is_anomalous"] = hop.get("is_anomalous", False) or False
    return hops


def _try_parse_date(raw):
    if not raw:
        return None
    try:
        return parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None


def score_risk(auth_results: dict, hops: list[dict], has_received_headers: bool) -> tuple[int, str, bool]:
    """
    Produce a 0-100 risk score plus a human-readable summary and a
    is_spoof_suspected boolean, from authentication results and hop anomalies.
    """
    score = 0
    reasons = []

    if auth_results.get("spf") in ("fail", "softfail"):
        score += 25
        reasons.append(f"SPF check {auth_results.get('spf')}")
    if auth_results.get("dkim") in ("fail", "none"):
        score += 25
        reasons.append(f"DKIM {auth_results.get('dkim') or 'missing'}")
    if auth_results.get("dmarc") in ("fail", "none"):
        score += 20
        reasons.append(f"DMARC {auth_results.get('dmarc') or 'missing'}")

    anomalous_hops = [h for h in hops if h.get("is_anomalous")]
    if anomalous_hops:
        score += min(30, 15 * len(anomalous_hops))
        reasons.append(f"{len(anomalous_hops)} routing hop(s) with chronology anomalies")

    if not has_received_headers:
        score += 15
        reasons.append("No Received: headers present — routing history cannot be verified")

    score = min(score, 100)
    summary = "; ".join(reasons) if reasons else "No authentication or routing anomalies detected."
    is_spoof_suspected = score >= 40

    return score, summary, is_spoof_suspected
