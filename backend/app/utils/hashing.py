import hashlib


def sha256_bytes(data: bytes) -> str:
    """Return the SHA-256 hex digest of raw bytes, for chain-of-custody evidence integrity."""
    return hashlib.sha256(data).hexdigest()
