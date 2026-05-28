"""Entra JWT validation middleware (the edge APIM forwards the caller token — JWT pass-through,
per the design's APIM decision). Validates audience + issuer against the tenant JWKS and (optionally)
an OID allow-list (the agent SP + the n8n app). Disable for local dev with AUTH_DISABLED=true.

NB: APIM in front also does validate-jwt + rate-limit; this is defence-in-depth at the MCP itself.
"""
from __future__ import annotations

import logging
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)
_OPEN_PATHS = ("/healthz", "/health")


class EntraJWTMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.disabled = os.getenv("AUTH_DISABLED", "false").lower() == "true"
        self.audience = os.getenv("APIM_AUDIENCE", "")          # e.g. api://<apimAppId>
        self.tenant = os.getenv("ENTRA_TENANT", "")
        self.allowed_oids = {o for o in os.getenv("ALLOWED_OIDS", "").split(",") if o}
        self._jwk_client = None

    def _jwks(self):
        if self._jwk_client is None:
            from jwt import PyJWKClient
            self._jwk_client = PyJWKClient(
                f"https://login.microsoftonline.com/{self.tenant}/discovery/v2.0/keys"
            )
        return self._jwk_client

    async def dispatch(self, request: Request, call_next):
        if self.disabled or request.url.path in _OPEN_PATHS:
            return await call_next(request)
        if not (self.audience and self.tenant):
            logger.error("auth misconfigured: APIM_AUDIENCE/ENTRA_TENANT unset")
            return JSONResponse({"error": "auth misconfigured"}, status_code=500)
        auth = request.headers.get("authorization", "")
        if not auth.lower().startswith("bearer "):
            return JSONResponse({"error": "missing bearer token"}, status_code=401)
        token = auth.split(" ", 1)[1]
        try:
            import jwt
            signing_key = self._jwks().get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token, signing_key, algorithms=["RS256"], audience=self.audience,
                issuer=f"https://login.microsoftonline.com/{self.tenant}/v2.0",
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("JWT rejected: %s", e)
            return JSONResponse({"error": "invalid token"}, status_code=401)
        if self.allowed_oids and claims.get("oid") not in self.allowed_oids:
            return JSONResponse({"error": "caller not allowed"}, status_code=403)
        request.state.caller = claims.get("oid")
        return await call_next(request)
