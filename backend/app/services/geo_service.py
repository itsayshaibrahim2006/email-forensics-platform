"""
geo_service.py
---------------
Parses the Received: header chain (hop by hop, in transmission order) and
geolocates each hop's IP address.

Uses ip-api.com by default (free, no key, fine for a hackathon demo but rate
limited to ~45 req/min). Swap `geolocate_ip` for a MaxMind GeoLite2 offline
lookup in production to avoid the rate limit and external dependency.
"""
import re
import requests

from app.config import settings
from app.services.email_parser import extract_ips_from_received

HOSTNAME_REGEX = re.compile(r"from\s+([a-zA-Z0-9.\-]+)")
TIMESTAMP_REGEX = re.compile(r";\s*(.+)$")

_geo_cache: dict[str, dict] = {}

PRIVATE_IP_PREFIXES = ("10.", "127.", "192.168.", "169.254.")


def _is_private(ip: str) -> bool:
    if ip.startswith(PRIVATE_IP_PREFIXES):
        return True
    if ip.startswith("172."):
        try:
            second = int(ip.split(".")[1])
            return 16 <= second <= 31
        except (IndexError, ValueError):
            return False
    return False


def geolocate_ip(ip: str) -> dict:
    """Look up an IP's approximate geographic origin. Cached per-process."""
    if ip in _geo_cache:
        return _geo_cache[ip]

    if _is_private(ip):
        result = {"country": "Private/Internal", "city": None, "isp": None,
                  "asn": None, "latitude": None, "longitude": None}
        _geo_cache[ip] = result
        return result

    result = {"country": None, "city": None, "isp": None, "asn": None,
              "latitude": None, "longitude": None}
    try:
        url = settings.geo_api_url.format(ip=ip)
        resp = requests.get(url, timeout=3)
        if resp.ok:
            data = resp.json()
            if data.get("status") != "fail":
                result = {
                    "country": data.get("country"),
                    "city": data.get("city"),
                    "isp": data.get("isp"),
                    "asn": data.get("as"),
                    "latitude": data.get("lat"),
                    "longitude": data.get("lon"),
                }
    except requests.RequestException:
        # Network unavailable / rate-limited — degrade gracefully, don't crash ingest
        pass

    _geo_cache[ip] = result
    return result


def build_hop_chain(received_headers: list[str]) -> list[dict]:
    """
    Convert a list of raw Received: header strings (as returned by the email
    parser, which are in top-to-bottom / most-recent-first order) into an
    ordered, geolocated hop chain from origin -> destination.
    """
    # Received headers appear newest-first in the raw message; reverse so
    # hop_index 0 is the originating server.
    ordered = list(reversed(received_headers))

    hops = []
    for idx, header in enumerate(ordered):
        ips = extract_ips_from_received(header)
        ip = ips[0] if ips else None
        hostname_match = HOSTNAME_REGEX.search(header)
        hostname = hostname_match.group(1) if hostname_match else None
        ts_match = TIMESTAMP_REGEX.search(header)
        timestamp_raw = ts_match.group(1).strip() if ts_match else None

        geo = geolocate_ip(ip) if ip else {"country": None, "city": None,
                                            "isp": None, "asn": None,
                                            "latitude": None, "longitude": None}

        hops.append({
            "hop_index": idx,
            "ip_address": ip,
            "hostname": hostname,
            "timestamp_raw": timestamp_raw,
            **geo,
        })

    return hops
