"""
JWKS-based multi-tenant JWT verification tests

Covers:
- JWKS kid selection and signature validation
- Issuer and audience enforcement
- Missing kid when JWKS required
- PEM fallback path when JWKS is not configured
"""

from __future__ import annotations

import base64
from typing import Dict, Any
from datetime import datetime, timedelta, timezone

import pytest
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from infra.auth.jwt_auth import verify_jwt_token
from models.tenant import TenantConfig
from api.dependencies.tenant_manager import get_tenant_manager, TenantManager


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _gen_rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    numbers = public_key.public_numbers()
    n = numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, byteorder="big")
    e = numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, byteorder="big")
    jwk = {
        "kty": "RSA",
        "kid": "test-kid",
        "n": _b64url(n),
        "e": _b64url(e),
        "alg": "RS256",
        "use": "sig",
    }
    return priv_pem, pub_pem, jwk


@pytest.mark.asyncio
async def test_verify_with_jwks(monkeypatch):
    """Verify token using JWKS kid selection."""
    enable_jwks = True
    priv_pem, pub_pem, jwk = _gen_rsa_keypair()
    jwks_uri = "https://issuer.example.com/.well-known/jwks.json"
    issuer = "https://issuer.example.com/"
    audience = "mas-api"

    # Monkeypatch httpx AsyncClient.get to return our JWKS
    class MockResp:
        def __init__(self, json_data: Dict[str, Any]):
            self._json = json_data
            self.status_code = 200
            self.headers = {"ETag": "W/\"123\""}

        def json(self):
            return self._json

        def raise_for_status(self):
            return None

    async def mock_get(self, url, headers=None):
        assert url == jwks_uri
        return MockResp({"keys": [jwk]})

    import httpx

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    # Prepare tenant config
    manager: TenantManager = await get_tenant_manager()
    cfg = TenantConfig(
        tenant_id="tenant_jwks",
        tenant_name="Tenant JWKS",
        issuer=issuer,
        jwks_uri=jwks_uri,
        allowed_algorithms=["RS256"],
        require_kid=True,
        jwt_issuer=issuer,
        jwt_audience=audience,
        token_expiry_hours=1,
        max_token_age_minutes=10,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        is_active=True,
    )
    await manager.save_tenant_config(cfg)

    # Create JWT
    now = datetime.now(timezone.utc)
    payload = {
        "tenant_id": "tenant_jwks",
        "sub": "user_1",
        "iss": issuer,
        "aud": audience,
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "iat": int(now.timestamp()),
        "jti": "jti-123",
    }
    headers = {"kid": jwk["kid"]}
    token = jwt.encode(payload, priv_pem, algorithm="RS256", headers=headers)

    # Verify
    result = await verify_jwt_token(token, manager)
    assert result.is_valid is True
    assert result.tenant_context is not None
    assert result.tenant_context.tenant_id == "tenant_jwks"


@pytest.mark.asyncio
async def test_verify_with_pem_fallback():
    """Verify token when only PEM is configured (no JWKS)."""
    priv_pem, pub_pem, _ = _gen_rsa_keypair()
    issuer = "mas-cosmetic-system"
    audience = "mas-api"
    manager: TenantManager = await get_tenant_manager()

    cfg = TenantConfig(
        tenant_id="tenant_pem",
        tenant_name="Tenant PEM",
        jwt_public_key=pub_pem.decode("utf-8"),
        jwt_algorithm="RS256",
        jwt_issuer=issuer,
        jwt_audience=audience,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        is_active=True,
    )
    await manager.save_tenant_config(cfg)

    now = datetime.now(timezone.utc)
    payload = {
        "tenant_id": "tenant_pem",
        "sub": "user_2",
        "iss": issuer,
        "aud": audience,
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "iat": int(now.timestamp()),
        "jti": "jti-456",
    }
    token = jwt.encode(payload, priv_pem, algorithm="RS256")

    result = await verify_jwt_token(token, manager)
    assert result.is_valid is True
    assert result.tenant_context is not None
    assert result.tenant_context.tenant_id == "tenant_pem"


@pytest.mark.asyncio
async def test_invalid_issuer_rejected(monkeypatch):
    """Invalid issuer must be rejected."""
    priv_pem, pub_pem, jwk = _gen_rsa_keypair()
    jwks_uri = "https://issuer.example.com/.well-known/jwks.json"
    issuer = "https://issuer.example.com/"
    audience = "mas-api"

    class MockResp:
        def __init__(self, json_data: Dict[str, Any]):
            self._json = json_data
            self.status_code = 200
            self.headers = {}

        def json(self):
            return self._json

        def raise_for_status(self):
            return None

    async def mock_get(self, url, headers=None):
        return MockResp({"keys": [jwk]})

    import httpx

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    manager: TenantManager = await get_tenant_manager()
    cfg = TenantConfig(
        tenant_id="tenant_bad_iss",
        tenant_name="Bad Issuer",
        issuer=issuer,
        jwks_uri=jwks_uri,
        jwt_issuer=issuer,
        jwt_audience=audience,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        is_active=True,
    )
    await manager.save_tenant_config(cfg)

    now = datetime.now(timezone.utc)
    payload = {
        "tenant_id": "tenant_bad_iss",
        "sub": "user_3",
        "iss": "https://evil-issuer/",  # wrong issuer
        "aud": audience,
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "iat": int(now.timestamp()),
        "jti": "jti-789",
    }
    token = jwt.encode(payload, priv_pem, algorithm="RS256", headers={"kid": jwk["kid"]})

    result = await verify_jwt_token(token, manager)
    assert result.is_valid is False
    assert result.error_code == "INVALID_ISSUER"


@pytest.mark.asyncio
async def test_missing_kid_when_required(monkeypatch):
    """Missing kid should fail when JWKS is configured and kid required."""
    priv_pem, pub_pem, jwk = _gen_rsa_keypair()
    jwks_uri = "https://issuer.example.com/.well-known/jwks.json"
    issuer = "https://issuer.example.com/"
    audience = "mas-api"

    class MockResp:
        def __init__(self, json_data: Dict[str, Any]):
            self._json = json_data
            self.status_code = 200
            self.headers = {}

        def json(self):
            return self._json

        def raise_for_status(self):
            return None

    async def mock_get(self, url, headers=None):
        return MockResp({"keys": [jwk]})

    import httpx

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    manager: TenantManager = await get_tenant_manager()
    cfg = TenantConfig(
        tenant_id="tenant_missing_kid",
        tenant_name="Missing KID",
        issuer=issuer,
        jwks_uri=jwks_uri,
        require_kid=True,
        jwt_issuer=issuer,
        jwt_audience=audience,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        is_active=True,
    )
    await manager.save_tenant_config(cfg)

    now = datetime.now(timezone.utc)
    payload = {
        "tenant_id": "tenant_missing_kid",
        "sub": "user_4",
        "iss": issuer,
        "aud": audience,
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "iat": int(now.timestamp()),
        "jti": "jti-999",
    }
    token = jwt.encode(payload, priv_pem, algorithm="RS256")  # no kid header

    result = await verify_jwt_token(token, manager)
    assert result.is_valid is False
    assert result.error_code == "MISSING_KID"


