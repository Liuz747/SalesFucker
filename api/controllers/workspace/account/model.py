"""
租户管理数据模型

包含租户管理相关的业务模型和数据库模型，支持多租户架构。
提供租户配置、权限控制、审计日志等完整功能。

主要模型:
- Tenant: 租户配置业务模型
"""

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field


class Tenant(BaseModel):
    """
    租户配置业务模型
    
    存储租户的完整业务配置信息，包括品牌设置、AI偏好、
    功能开关、访问控制等。用于业务逻辑处理。
    """
    
    # 基本信息
    tenant_id: str = Field(description="租户标识符")
    tenant_name: str = Field(description="租户名称")
    status: int = Field(default=1, description="状态：1-活跃，0-禁用")
    
    # 业务信息
    industry: int = Field(default=1, description="行业类型：1-美容诊所，2-化妆品公司等")
    company_size: Optional[int] = Field(default=1, description="公司规模：1-小型，2-中型，3-大型") 
    area_id: int = Field(default=1, description="地区ID")
    user_count: int = Field(default=0, description="用户数量")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    
    # 审计字段
    creator: int = Field(default=1, description="创建者ID")
    editor: Optional[int] = Field(None, description="编辑者ID")
    deleted: bool = Field(default=False, description="删除标记")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="最后更新时间")
    
    # 业务配置
    feature_flags: Dict[str, bool] = Field(
        default_factory=dict, 
        description="功能开关配置"
    )