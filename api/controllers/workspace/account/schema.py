from datetime import datetime
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field

class TenantSyncRequest(BaseModel):
    tenant_id: str = Field(description="租户ID")
    tenant_name: str = Field(description="租户名称")
    status: int = Field(default=1, description="状态：1-活跃，0-禁用")
    industry: int = Field(default=1, description="行业类型：1-美容诊所，2-化妆品公司等")
    area_id: int = Field(default=1, description="地区ID")
    creator: int = Field(default=1, description="创建者ID")
    company_size: Optional[int] = Field(default=1, description="公司规模：1-小型，2-中型，3-大型")
    features: Optional[List[str]] = Field(default=None, description="启用的功能")


class TenantUpdateRequest(BaseModel):
    features: Optional[List[str]] = Field(None, description="功能列表")
    status: Optional[int] = Field(None, description="状态：1-活跃，0-禁用")


class TenantSyncResponse(BaseModel):
    tenant_id: str
    message: str
    synced_at: datetime
    features_enabled: Optional[List[str]] = None


class TenantStatusResponse(BaseModel):
    tenant_id: str
    tenant_name: Optional[str] = None
    status: int
    updated_at: Optional[datetime] = None


class TenantListResponse(BaseModel):
    total: int
    tenants: List[Dict[str, Any]]
