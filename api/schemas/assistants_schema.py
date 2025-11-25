"""
AI员工管理相关数据模型

该模块定义了AI员工管理相关的请求和响应数据模型，支持助理的创建、
配置、查询和管理等完整生命周期。

核心模型:
- AssistantCreateRequest: 创建助理请求
- AssistantUpdateRequest: 更新助理请求
- AssistantResponse: 助理响应
- AssistantListResponse: 助理列表响应
"""

from datetime import datetime
from enum import StrEnum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from .prompts_schema import AssistantPromptConfig


class AssistantStatus(StrEnum):
    """助理状态枚举"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    TRAINING = "training"


class AssistantCreateRequest(BaseModel):
    """
    创建AI员工请求模型
    """

    tenant_id: str = Field(description="租户标识符", min_length=1, max_length=100)
    assistant_name: str = Field(description="助理姓名", min_length=1, max_length=100)
    nickname: Optional[str] = Field(None, description="助理昵称", max_length=100)
    address: Optional[str] = Field(None, description="助理地址", max_length=500)
    sex: Optional[str] = Field(None, description="助理性别", max_length=32)

    # 助理配置
    personality: str = Field(description="助理个性类型（优先使用 prompt_config）")
    occupation: str = Field(description="数字员工职业")

    # 提示词配置
    prompt_config: Optional[AssistantPromptConfig] = Field(None, description="智能体提示词配置 - 定义个性、行为和交互方式")
    voice_id: str = Field(description="语音克隆配置，使用MiniMax模型")
    voice_file: Optional[str] = Field(None, description="语音文件URL链接", max_length=1024)

    # 专业领域
    industry: str = Field(description="数字员工所处的行业（如：护肤、彩妆、香水等）")

    # 个人资料
    profile: Optional[dict[str, Any]] = Field(None, description="助理个人资料信息")

    @field_validator("assistant_name")
    def validate_assistant_name(cls, v):
        """验证助理姓名"""
        if not v or not v.strip():
            raise ValueError("助理姓名不能为空")
        return v.strip()


class AssistantUpdateRequest(BaseModel):
    """
    更新AI员工请求模型
    """
    assistant_name: Optional[str] = Field(None, description="助理姓名", min_length=1, max_length=100)
    nickname: Optional[str] = Field(None, description="助理昵称", max_length=100)
    address: Optional[str] = Field(None, description="助理地址", max_length=500)
    sex: Optional[str] = Field(None, description="助理性别", max_length=32)
    personality: Optional[str] = Field(None, description="助理个性类型")
    occupation: Optional[str] = Field(None, description="数字员工职业")

    # 提示词配置更新
    prompt_config: Optional[AssistantPromptConfig] = Field(None, description="智能体提示词配置更新")
    voice_id: Optional[str] = Field(None, description="语音克隆配置")
    voice_file: Optional[str] = Field(None, description="语音文件URL链接", max_length=1024)
    industry: Optional[str] = Field(None, description="数字员工所在行业（如：护肤、彩妆、香水等）")
    profile: Optional[dict[str, Any]] = Field(None, description="助理个人资料信息")
    status: Optional[AssistantStatus] = Field(None, description="助理状态")


# 响应模型
class AssistantResponse(BaseModel):
    """
    AI员工响应模型
    """

    assistant_id: str = Field(description="助理ID")
    assistant_name: str = Field(description="助理姓名")
    tenant_id: str = Field(description="租户ID")
    nickname: Optional[str] = Field(None, description="数字员工昵称")

    # 基本信息
    status: AssistantStatus = Field(description="助理状态")
    sex: Optional[str] = Field(None, description="数字员工性别")
    address: Optional[str] = Field(None, description="数字员工公司地址")
    personality: str = Field(description="个性类型")
    occupation: str = Field(description="数字员工职业")

    # 配置信息
    voice_id: str = Field(description="语音语调配置")
    voice_file: Optional[str] = Field(None, description="语音文件URL链接")
    profile: Optional[dict[str, Any]] = Field(None, description="个人资料信息")
    industry: str = Field(description="数字员工所处行业")

    # 时间信息
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
    last_active_at: Optional[datetime] = Field(None, description="最后活跃时间")


class AssistantDeleteResponse(BaseModel):
    """
    删除助理响应模型
    """
    is_delete: bool = Field(description="是否有删除操作")
