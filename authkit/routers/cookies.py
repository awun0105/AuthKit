"""Optional HttpOnly refresh-cookie helpers for browser clients.

Bearer JSON refresh remains the default. Cookie mode is additive.
"""

from __future__ import annotations

from fastapi import HTTPException, Request, Response

from authkit.core.config import AuthKitConfig

CSRF_HEADER = "x-authkit-requested-with"
CSRF_HEADER_VALUE = "AuthKit"


def set_refresh_cookies(response: Response, refresh_token: str, config: AuthKitConfig) -> None:
    if not config.enable_refresh_cookie:
        return
    response.set_cookie(
        key=config.refresh_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=config.refresh_cookie_secure,
        samesite=config.refresh_cookie_samesite,
        max_age=config.refresh_token_ttl,
        path=config.refresh_cookie_path,
        domain=config.refresh_cookie_domain,
    )
    # Non-secret UX flag for Next.js middleware redirects. Not a security boundary.
    response.set_cookie(
        key=config.authenticated_cookie_name,
        value="1",
        httponly=False,
        secure=config.refresh_cookie_secure,
        samesite=config.refresh_cookie_samesite,
        max_age=config.refresh_token_ttl,
        path="/",
        domain=config.refresh_cookie_domain,
    )


def clear_refresh_cookies(response: Response, config: AuthKitConfig) -> None:
    if not config.enable_refresh_cookie:
        return
    response.delete_cookie(
        key=config.refresh_cookie_name,
        path=config.refresh_cookie_path,
        domain=config.refresh_cookie_domain,
    )
    response.delete_cookie(
        key=config.authenticated_cookie_name,
        path="/",
        domain=config.refresh_cookie_domain,
    )


def refresh_token_from_request(
    request: Request,
    body_token: str | None,
    config: AuthKitConfig,
) -> str:
    if body_token:
        return body_token
    if config.enable_refresh_cookie:
        cookie_token = request.cookies.get(config.refresh_cookie_name)
        if cookie_token:
            enforce_cookie_csrf(request)
            return cookie_token
    raise HTTPException(status_code=400, detail="Refresh token is required")


def enforce_cookie_csrf(request: Request) -> None:
    """Reject cookie-authenticated mutations that lack the custom header.

    Cross-site HTML form posts cannot set this header. Same-site XHR from the
    AuthKit client always sends it. SameSite=Lax is additional defense, not
    the only control.
    """
    if request.headers.get(CSRF_HEADER) != CSRF_HEADER_VALUE:
        raise HTTPException(
            status_code=403,
            detail="CSRF check failed",
            headers={"X-AuthKit-Error": "CSRF_FAILED"},
        )
