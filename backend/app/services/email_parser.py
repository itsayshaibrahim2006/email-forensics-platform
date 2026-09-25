"""
email_parser.py
----------------
Parses raw .eml bytes into structured forensic data: headers, thread-linking
fields (Message-ID / In-Reply-To / References), body preview, and the raw
Received: header chain (used later for geolocation).

Uses only Python's standard library `email` module so it has zero external
dependencies and behaves predictably on malformed/real-world email.
"""
import re
from email import message_from_bytes
from email.policy import default as default_policy
from email.utils import getaddresses, parsedate_to_datetime


def parse_eml(raw_bytes: bytes) -> dict:
    msg = message_from_bytes(raw_bytes, policy=default_policy)

    message_id = _clean_id(msg.get("Message-ID"))
    in_reply_to = _clean_id(msg.get("In-Reply-To"))
    references_raw = msg.get("References", "") or ""
    references = [_clean_id(r) for r in references_raw.split() if r.strip()]

    subject = msg.get("Subject", "") or ""
    sender = msg.get("From", "") or ""
    to_list = [addr for _, addr in getaddresses(msg.get_all("To", []))]
    recipients = ", ".join(to_list)

    date_header = msg.get("Date")
    date_sent = date_header
    try:
        if date_header:
            parsedate_to_datetime(date_header)  # validates parseability
    except Exception:
        pass

    body_preview = _extract_body_preview(msg)

    # Collect ALL headers for the forensic record (raw_headers JSON field)
    raw_headers = {}
    for key in msg.keys():
        values = msg.get_all(key)
        raw_headers[key] = values if len(values) > 1 else values[0]

    received_chain = msg.get_all("Received", []) or []
    auth_results = msg.get_all("Authentication-Results", []) or []

    return {
        "message_id": message_id,
        "in_reply_to": in_reply_to,
        "references": references,
        "subject": subject,
        "sender": sender,
        "recipients": recipients,
        "date_sent": date_sent,
        "body_preview": body_preview,
        "raw_headers": raw_headers,
        "received_chain": received_chain,
        "authentication_results": auth_results,
    }


def _clean_id(value):
    if not value:
        return None
    return value.strip().strip("<>")


def _extract_body_preview(msg, max_len: int = 500) -> str:
    """Return a plain-text preview of the email body, stripping quoted reply text."""
    text = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get_filename():
                try:
                    text = part.get_content()
                except Exception:
                    text = ""
                break
    else:
        try:
            text = msg.get_content()
        except Exception:
            text = ""

    if not isinstance(text, str):
        text = str(text)

    # Strip common quoted-reply markers (">", "On ... wrote:") for a cleaner preview
    lines = []
    for line in text.splitlines():
        if line.strip().startswith(">"):
            continue
        if re.match(r"^On .* wrote:$", line.strip()):
            break
        lines.append(line)

    cleaned = "\n".join(lines).strip()
    return cleaned[:max_len]


IP_REGEX = re.compile(
    r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b"
)


def extract_ips_from_received(received_header: str):
    """Return all IPv4 addresses found in a single Received: header line."""
    return IP_REGEX.findall(received_header)
