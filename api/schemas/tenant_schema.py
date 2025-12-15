from typing import Optional

from pydantic import BaseModel, Field

from libs.types import AccountStatus


class TenantSyncRequest(BaseModel):
    tenant_id: str = Field(description="租户ID")
    tenant_name: Optional[str] = Field(None, description="租户名称")
    status: AccountStatus = Field(default=AccountStatus.ACTIVE, description="租户状态")
    industry: Optional[str] = Field(description="行业类型")
    creator: Optional[int] = Field(description="创建者ID")


class TenantUpdateRequest(BaseModel):
    status: Optional[AccountStatus] = Field(None, description="租户状态")
