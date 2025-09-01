"""
Service JWT authentication tests

Covers:
- Service JWT token verification with RSA keys
- Service context extraction and validation
- Invalid token rejection
- Expired token handling
"""

from __future__ import annotations

import sys
import os
import jwt
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from infra.auth.jwt_auth import verify_service_token, ServiceContext
from infra.auth.key_manager import key_manager
from config import settings


@pytest.mark.asyncio
async def test_success():
    """Test successful service token verification."""
    # Generate test key pair
    app_key = "test-service"
    key_data = key_manager.generate_key_pair(app_key)
    
    # Mock settings
    with patch.object(settings, 'APP_KEY', app_key), \
         patch.object(settings, 'APP_JWT_ISSUER', 'mas-cosmetic-system'), \
         patch.object(settings, 'APP_JWT_AUDIENCE', 'mas-api'):
        
        # Create test token
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "backend-service",
            "iss": "mas-cosmetic-system",
            "aud": "mas-api",
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "iat": int(now.timestamp()),
            "jti": "test-jti-123",
            "scope": ["backend:read", "backend:write"]
        }
        
        token = jwt.encode(payload, key_data["private_key"], algorithm="RS256")
        
        # Verify token
        result = await verify_service_token(token)
        
        assert result.is_valid is True
        assert result.service_context is not None
        assert result.service_context.sub == "backend-service"
        assert result.service_context.iss == "mas-cosmetic-system"
        assert result.service_context.aud == "mas-api"
        assert result.service_context.jti == "test-jti-123"
        assert "backend:read" in result.service_context.scopes
        assert "backend:write" in result.service_context.scopes


@pytest.mark.asyncio
async def test_token_expired():
    """Test expired service token rejection."""
    app_key = "test-service-expired"
    key_data = key_manager.generate_key_pair(app_key)
    
    with patch.object(settings, 'APP_KEY', app_key), \
         patch.object(settings, 'APP_JWT_ISSUER', 'mas-cosmetic-system'), \
         patch.object(settings, 'APP_JWT_AUDIENCE', 'mas-api'):
        
        # Create expired token
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "backend-service",
            "iss": "mas-cosmetic-system",
            "aud": "mas-api",
            "exp": int((now - timedelta(minutes=5)).timestamp()),  # Expired 5 minutes ago
            "iat": int((now - timedelta(minutes=10)).timestamp()),
            "jti": "expired-jti-123",
            "scope": ["backend:read"]
        }
        
        token = jwt.encode(payload, key_data["private_key"], algorithm="RS256")
        
        # Verify token
        result = await verify_service_token(token)
        
        assert result.is_valid is False
        assert result.error_code == "SERVICE_TOKEN_EXPIRED"
        assert result.service_context is None


@pytest.mark.asyncio
async def test_invalid_subject():
    """Test rejection of token with invalid subject."""
    app_key = "test-service-invalid-sub"
    key_data = key_manager.generate_key_pair(app_key)
    
    with patch.object(settings, 'APP_KEY', app_key), \
         patch.object(settings, 'APP_JWT_ISSUER', 'mas-cosmetic-system'), \
         patch.object(settings, 'APP_JWT_AUDIENCE', 'mas-api'):
        
        # Create token with invalid subject
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "invalid-service",  # Wrong subject
            "iss": "mas-cosmetic-system",
            "aud": "mas-api",
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "iat": int(now.timestamp()),
            "jti": "invalid-sub-jti-123",
            "scope": ["backend:read"]
        }
        
        token = jwt.encode(payload, key_data["private_key"], algorithm="RS256")
        
        # Verify token
        result = await verify_service_token(token)
        
        assert result.is_valid is False
        assert result.error_code == "INVALID_SERVICE_SUBJECT"
        assert result.service_context is None


@pytest.mark.asyncio
async def test_invalid_issuer():
    """Test rejection of token with invalid issuer."""
    app_key = "test-service-invalid-iss"
    key_data = key_manager.generate_key_pair(app_key)
    
    with patch.object(settings, 'APP_KEY', app_key), \
         patch.object(settings, 'APP_JWT_ISSUER', 'mas-cosmetic-system'), \
         patch.object(settings, 'APP_JWT_AUDIENCE', 'mas-api'):
        
        # Create token with invalid issuer
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "backend-service",
            "iss": "evil-issuer",  # Wrong issuer
            "aud": "mas-api",
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "iat": int(now.timestamp()),
            "jti": "invalid-iss-jti-123",
            "scope": ["backend:read"]
        }
        
        token = jwt.encode(payload, key_data["private_key"], algorithm="RS256")
        
        # Verify token
        result = await verify_service_token(token)
        
        assert result.is_valid is False
        assert result.error_code == "INVALID_SERVICE_TOKEN"
        assert result.service_context is None


@pytest.mark.asyncio
async def test_no_app_key():
    """Test failure when APP_KEY is not configured."""
    with patch.object(settings, 'APP_KEY', None):
        # Verify token without app key
        result = await verify_service_token("dummy-token")
        
        assert result.is_valid is False
        assert result.error_code == "SERVICE_AUTH_NOT_CONFIGURED"
        assert result.service_context is None


@pytest.mark.asyncio
async def test_key_not_found():
    """Test failure when key pair is not found."""
    with patch.object(settings, 'APP_KEY', 'non-existent-key'):
        # Verify token with non-existent key
        result = await verify_service_token("dummy-token")
        
        assert result.is_valid is False
        assert result.error_code == "SERVICE_KEY_NOT_FOUND"
        assert result.service_context is None


def test_service_scopes():
    """Test ServiceContext scope checking methods."""
    context = ServiceContext(
        sub="backend-service",
        iss="mas-cosmetic-system",
        aud="mas-api",
        exp=datetime.now(timezone.utc) + timedelta(hours=1),
        iat=datetime.now(timezone.utc),
        jti="test-jti",
        scopes=["backend:read", "backend:write", "backend:admin"],
        token_source="test",
        verification_timestamp=datetime.now(timezone.utc)
    )
    
    # Test scope checking
    assert context.has_scope("backend:read") is True
    assert context.has_scope("backend:write") is True
    assert context.has_scope("backend:admin") is True
    assert context.has_scope("invalid:scope") is False
    
    # Test admin checking
    assert context.is_admin() is True
    
    # Test context without admin scope
    context_no_admin = ServiceContext(
        sub="backend-service",
        iss="mas-cosmetic-system",
        aud="mas-api",
        exp=datetime.now(timezone.utc) + timedelta(hours=1),
        iat=datetime.now(timezone.utc),
        jti="test-jti-2",
        scopes=["backend:read"],
        token_source="test",
        verification_timestamp=datetime.now(timezone.utc)
    )
    
    assert context_no_admin.has_scope("backend:read") is True
    assert context_no_admin.has_scope("backend:admin") is False
    assert context_no_admin.is_admin() is False