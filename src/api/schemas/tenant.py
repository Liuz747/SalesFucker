from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, HttpUrl


class TenantSyncRequest(BaseModel):
    tenant_id: str = Field(description="租户ID")
    tenant_name: Optional[str] = Field(None, description="租户名称")
    issuer: Optional[str] = Field(None, description="JWT颁发者(iss)")
    jwks_uri: Optional[HttpUrl] = Field(None, description="JWKS地址")
    jwt_public_key: Optional[str] = Field(
        None, description="PEM公钥(仅作为回退方案)"
    )
    features: Optional[List[str]] = Field(default=None, description="启用的功能")
    is_active: bool = Field(default=True, description="是否激活")


class TenantUpdateRequest(BaseModel):
    issuer: Optional[str] = Field(None, description="JWT颁发者(iss)")
    jwks_uri: Optional[HttpUrl] = Field(None, description="JWKS地址")
    jwt_public_key: Optional[str] = Field(None, description="PEM公钥(回退)")
    features: Optional[List[str]] = Field(None, description="功能列表")
    is_active: Optional[bool] = Field(None, description="是否激活")


class TenantSyncResponse(BaseModel):
    tenant_id: str
    sync_status: str
    message: str
    synced_at: datetime
    features_enabled: Optional[List[str]] = None
    public_key_fingerprint: Optional[str] = None


class TenantStatusResponse(BaseModel):
    tenant_id: str
    tenant_name: Optional[str] = None
    is_active: bool
    issuer: Optional[str] = None
    jwks_uri: Optional[str] = None
    has_public_key: bool = False
    updated_at: Optional[datetime] = None
    last_access: Optional[datetime] = None


class TenantListResponse(BaseModel):
    total: int
    tenants: List[Dict[str, Any]]


