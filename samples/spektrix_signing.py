"""
Spektrix API v3 — HMAC-SHA1 request signing.

Every request to Spektrix carries a Date header and an Authorization
header computed over the request method, full URL, and date string. For
non-GET requests, a Base64-encoded MD5 of the body is appended to the
signed string.

Signing algorithm (per https://integrate.spektrix.com/docs/authentication):
    StringToSign  = HTTP-Method + "\\n" + Full-URL + "\\n" + UTC-Date
                    (+ "\\n" + Base64(MD5(body)) for non-GET requests)
    Signature     = Base64(HMAC-SHA1(Base64Decode(SecretKey), UTF-8(StringToSign)))
    Authorization = "SpektrixAPI3 " + LoginName + ":" + Signature

Sanitized excerpt. Transport helpers (get, post) and diagnostic test
functions are omitted; see ../docs/spektrix-integration.md for the
end-to-end integration context and 104-event validation results.
"""

import base64
import hashlib
import hmac
import os
from datetime import datetime, timezone
from email.utils import formatdate

# Credentials sourced from environment variables (loaded via standard means).
API_USER = os.environ.get("SPEKTRIX_API_USER", "")
API_KEY = os.environ.get("SPEKTRIX_API_KEY", "")


def _utc_date() -> str:
    """Return the current UTC time in RFC 7231 format (e.g. Mon, 21 Oct 2020 07:28:00 GMT)."""
    return formatdate(timeval=datetime.now(timezone.utc).timestamp(), usegmt=True)


def _sign_request(method: str, url: str, date: str, body: bytes = b"") -> str:
    """
    Build and return the value for the Authorization header.

    Args:
        method: HTTP verb in uppercase (e.g. "GET", "POST").
        url:    Full request URL including protocol and host.
        date:   RFC 7231 UTC date string (must match the Date header sent).
        body:   Raw request body bytes; empty for GET requests.

    Returns:
        Authorization header value, e.g. "SpektrixAPI3 MyUser:abc123==".
    """
    parts = [method.upper(), url, date]

    if body:
        md5_digest = hashlib.md5(body).digest()
        body_hash = base64.b64encode(md5_digest).decode("utf-8")
        parts.append(body_hash)

    string_to_sign = "\n".join(parts)

    decoded_key = base64.b64decode(API_KEY)
    signature_bytes = hmac.new(decoded_key, string_to_sign.encode("utf-8"), hashlib.sha1).digest()
    signature = base64.b64encode(signature_bytes).decode("utf-8")

    return f"SpektrixAPI3 {API_USER}:{signature}"


def _signed_headers(method: str, url: str, body: bytes = b"") -> dict:
    """Return the complete set of headers required for a signed Spektrix request."""
    date = _utc_date()
    return {
        "Date": date,
        "Authorization": _sign_request(method, url, date, body),
    }
