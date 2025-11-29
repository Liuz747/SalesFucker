from typing import Optional

from pydantic import BaseModel, Field

from libs.types import AccountStatus
from schemas.responses import BaseResponse


class BaseTenant(BaseModel):
    tenant_id: str = Field(description="租户ID")
    tenant_name: Optional[str] = Field(None, description="租户名称")
    status: AccountStatus = Field(default=AccountStatus.ACTIVE, description="租户状态")


class TenantSyncRequest(BaseTenant):
    industry: Optional[str] = Field(description="行业类型")
    creator: Optional[int] = Field(description="创建者ID")


class TenantUpdateRequest(BaseModel):
    status: Optional[AccountStatus] = Field(None, description="租户状态")


class TenantSyncResponse(BaseResponse, BaseTenant):
    pass


class TenantStatusResponse(BaseResponse, BaseTenant):
    pass


class TenantDeleteResponse(BaseResponse, BaseTenant):
    pass
