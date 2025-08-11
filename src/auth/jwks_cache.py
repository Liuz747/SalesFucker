"""
JWKS Fetching and Caching Utility (disabled in prototype)

Note: For rapid prototype with App-Key flow, JWKS usage is commented out.
This module remains for future re-enablement.
"""

from __future__ import annotations

import asyncio
import json
from typing import Dict, Optional, Any

import httpx
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


class JWKSCache:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def get_jwks(self, jwks_uri: str) -> Dict[str, Any]:
        async with self._lock:
            entry = self._cache.get(jwks_uri)
            headers = {}
            if entry and entry.get("etag"):
                headers["If-None-Match"] = entry["etag"]

        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(jwks_uri, headers=headers)

        if resp.status_code == 304 and entry:
            return entry["jwks"]

        resp.raise_for_status()
        jwks = resp.json()
        etag = resp.headers.get("ETag")

        async with self._lock:
            self._cache[jwks_uri] = {"jwks": jwks, "etag": etag}

        return jwks

    async def get_key_pem_by_kid(self, jwks_uri: str, kid: str) -> Optional[bytes]:
        jwks = await self.get_jwks(jwks_uri)
        keys = jwks.get("keys", [])
        for jwk in keys:
            if jwk.get("kid") == kid and jwk.get("kty") == "RSA":
                n_b64 = jwk.get("n")
                e_b64 = jwk.get("e")
                if not n_b64 or not e_b64:
                    continue
                # Convert base64url to int
                import base64

                def b64url_to_int(val: str) -> int:
                    padding = '=' * (-len(val) % 4)
                    return int.from_bytes(base64.urlsafe_b64decode(val + padding), 'big')

                n = b64url_to_int(n_b64)
                e = b64url_to_int(e_b64)
                public_numbers = rsa.RSAPublicNumbers(e, n)
                public_key = public_numbers.public_key(backend=default_backend())
                pem = public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )
                return pem
        return None


_global_jwks_cache: Optional[JWKSCache] = None


async def get_global_jwks_cache() -> JWKSCache:
    global _global_jwks_cache
    if _global_jwks_cache is None:
        _global_jwks_cache = JWKSCache()
    return _global_jwks_cache


