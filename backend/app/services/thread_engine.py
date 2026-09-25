"""
thread_engine.py
-----------------
Groups parsed emails into conversation threads.

Primary strategy: link by Message-ID / In-Reply-To / References (RFC 5322),
which is reliable whenever headers are intact.

Fallback strategy: when those headers are missing or stripped (common when
headers have been tampered with), fall back to normalized-subject grouping
("Re:"/"Fwd:" prefixes stripped, whitespace collapsed) as a best-effort
reconstruction. This is where a production system would instead use
sentence-embedding similarity over quoted body text; the interface below
(`find_thread_key`) is the seam where that upgrade plugs in.
"""
import re

RE_FWD_PREFIX = re.compile(r"^\s*(re|fwd?|fw)\s*:\s*", re.IGNORECASE)


def normalize_subject(subject: str) -> str:
    if not subject:
        return ""
    s = subject.strip()
    # Strip repeated Re:/Fwd: prefixes
    prev = None
    while prev != s:
        prev = s
        s = RE_FWD_PREFIX.sub("", s).strip()
    return re.sub(r"\s+", " ", s).lower()


def find_thread_key(parsed_email: dict) -> str:
    """
    Return the best available key to group this email into a thread.
    Prefers the first References entry (root of the thread) or In-Reply-To,
    falls back to the normalized subject when linking headers are absent.
    """
    if parsed_email.get("references"):
        return parsed_email["references"][0]
    if parsed_email.get("in_reply_to"):
        return parsed_email["in_reply_to"]
    if parsed_email.get("message_id"):
        # No reply linkage found -> this email is potentially a thread root.
        # We still key threads by normalized subject so later replies
        # (which may only share subject, not headers) can be matched to it.
        pass
    return "subj:" + normalize_subject(parsed_email.get("subject", ""))
