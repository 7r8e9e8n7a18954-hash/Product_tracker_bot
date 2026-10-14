from urllib.parse import urlparse
import ipaddress
import socket

ALLOWED_SCHEMES = {"http", "https"}

def validate_product_url(raw_url: str) -> tuple[bool, str]:
    """Validate a public web URL before storing it. This is not a complete fetch-time SSRF defense."""
    value = (raw_url or "").strip()
    if len(value) > 2048:
        return False, "Link is too long."
    parsed = urlparse(value)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return False, "Please send a link starting with http:// or https://."
    if not parsed.hostname:
        return False, "That link does not look valid."
    if parsed.username or parsed.password:
        return False, "Links containing embedded credentials are not accepted."
    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        return False, "Local/private network links are not accepted."
    try:
        # Reject literal non-public IP addresses.
        ip = ipaddress.ip_address(host)
        if not ip.is_global:
            return False, "Private or reserved IP addresses are not accepted."
    except ValueError:
        # Domain names are accepted at save-time; any future fetcher must re-resolve
        # DNS and validate every resolved IP immediately before connecting.
        pass
    return True, value

def is_public_ip(host: str) -> bool:
    """Helper for future HTTP adapters: every resolved address must pass this check."""
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        try:
            addresses = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        except OSError:
            return False
        return bool(addresses) and all(is_public_ip(item[4][0]) for item in addresses)
