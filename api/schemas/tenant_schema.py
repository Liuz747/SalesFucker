from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from models.enums import TenantStatus
from schemas.responses import BaseResponse


class BaseTenant(BaseModel):
    tenant_id: str = Field(description="租户ID")
    tenant_name: str = Field(description="租户名称")
    status: TenantStatus = Field(default=TenantStatus.ACTIVE, description="租户状态")
    updated_at: Optional[datetime] = Field(None, description="更新时间")


class FeatureFlags(BaseModel):
    """
    功能开关配置模型
    
    处理功能列表到字典的转换，封装业务逻辑。
    """
    enabled_features: Optional[bool] = Field(default_factory=bool, description="启用的功能列表")


class TenantSyncRequest(BaseTenant):
    industry: Optional[str] = Field(description="行业类型：1-美容诊所，2-化妆品公司等")
    area_id: Optional[str] = Field(description="地区ID")
    creator: Optional[int] = Field(description="创建者ID")
    company_size: Optional[int] = Field(default=1, description="公司规模：1-小型，2-中型，3-大型")
    features: Optional[FeatureFlags] = Field(default=None, description="启用的功能")


class TenantUpdateRequest(BaseTenant):
    features: Optional[dict[str, bool]] = Field(None, description="功能列表")


class TenantSyncResponse(BaseResponse, BaseTenant):
    features: Optional[FeatureFlags] = Field(None, description="启用的功能")


class TenantStatusResponse(BaseResponse, BaseTenant):
    pass


class TenantDeleteResponse(BaseResponse, BaseTenant):
    is_active: bool = Field(description="是否删除成功")