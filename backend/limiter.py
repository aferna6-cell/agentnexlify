from starlette.requests import Request
from slowapi import Limiter


def _get_real_client_ip(request: Request) -> str:
    """Extract the real client IP behind Railway's proxy.

    Railway (and most reverse proxies) append the real client IP as the
    *last* entry in X-Forwarded-For. An attacker can prepend fake IPs,
    but cannot control the last one added by the trusted proxy.

    Falls back to request.client.host if no forwarded header is present.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        # Last entry is the one added by Railway's proxy — most trustworthy
        ips = [ip.strip() for ip in forwarded.split(",") if ip.strip()]
        if ips:
            return ips[-1]
    return request.client.host if request.client else "127.0.0.1"


limiter = Limiter(key_func=_get_real_client_ip)
