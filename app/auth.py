from __future__ import annotations

import time
from functools import lru_cache
from typing import Any, Dict, Optional

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from .config import get_settings


class AuthError(HTTPException):
    def __init__(self, status_code: int = 401, detail: str = "Unauthorized") -> None:
        super().__init__(status_code=status_code, detail=detail)


@lru_cache(maxsize=1)
def _get_openid_config(issuer: str) -> Dict[str, Any]:
    well_known = issuer.rstrip("/") + "/.well-known/openid-configuration"
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(well_known)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise AuthError(500, f"Failed to fetch OIDC configuration from issuer: {e}")


@lru_cache(maxsize=1)
def _get_jwks(jwks_uri: str) -> Dict[str, Any]:
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(jwks_uri)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise AuthError(500, f"Failed to fetch JWKS: {e}")


def _decode_and_validate(token: str, audience: str, issuer: str) -> Dict[str, Any]:
    oidc = _get_openid_config(issuer)
    jwks = _get_jwks(oidc["jwks_uri"])

    # Use jose to verify signature via JWKS set
    # jose supports passing the JWKS as key parameter when options include algorithms
    try:
        unverified_headers = jwt.get_unverified_header(token)
    except JWTError as e:
        raise AuthError(401, f"Invalid token header: {e}")

    kid = unverified_headers.get("kid")
    if not kid:
        raise AuthError(401, "Token header missing 'kid'")

    # Find the matching key
    key = None
    for k in jwks.get("keys", []):
        if k.get("kid") == kid:
            key = k
            break
    if key is None:
        raise AuthError(401, "Matching JWK not found for token")

    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
            options={
                "verify_aud": True,
                "verify_iss": True,
                "verify_signature": True,
                "verify_exp": True,
            },
        )
    except JWTError as e:
        raise AuthError(401, f"Token validation failed: {e}")

    # Optional extra: nbf and iat checks (jose verifies exp by default)
    now = int(time.time())
    nbf = int(claims.get("nbf", 0))
    if nbf and now < nbf:
        raise AuthError(401, "Token not yet valid (nbf)")

    return claims


_http_bearer = HTTPBearer(auto_error=False)


def authenticate(credentials: Optional[HTTPAuthorizationCredentials] = Depends(_http_bearer)) -> Dict[str, Any]:
    """
    FastAPI dependency that authenticates the incoming request using Bearer JWT issued by Auth0.
    Returns the token claims on success. Raises HTTP 401/403 on failure.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthError(401, "Missing or invalid Authorization header")

    token = credentials.credentials
    settings = get_settings()
    if not settings.auth0_issuer or not settings.auth0_audience:
        raise AuthError(500, "Server auth configuration is incomplete")

    claims = _decode_and_validate(token, audience=settings.auth0_audience, issuer=settings.auth0_issuer)
    return claims


# A convenience dependency alias for readability in route signatures
AuthDependency = Depends(authenticate)
