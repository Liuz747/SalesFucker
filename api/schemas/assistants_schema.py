"""
AI员工管理相关数据模型

该模块定义了AI员工管理相关的请求和响应数据模型，支持助理的创建、
配置、查询和管理等完整生命周期。

核心模型:
- AssistantCreateRequest: 创建助理请求
- AssistantUpdateRequest: 更新助理请求
- AssistantDeleteResponse: 删除助理响应
"""

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from libs.types import AccountStatus


class AssistantCreateRequest(BaseModel):
    """
    创建AI员工请求模型
    """

    tenant_id: str = Field(description="租户标识符", min_length=1, max_length=100)
    assistant_name: str = Field(description="助理姓名", min_length=1, max_length=100)
    nickname: Optional[str] = Field(None, description="助理昵称", max_length=100)
    address: Optional[str] = Field(None, description="助理地址", max_length=500)
    sex: Optional[str] = Field(None, description="助理性别", max_length=32)
    personality: str = Field(description="助理个性类型")
    occupation: str = Field(description="数字员工职业")
    voice_id: Optional[str] = Field(None, description="语音克隆配置，使用MiniMax模型")
    voice_file: Optional[str] = Field(None, description="语音文件URL链接", max_length=1024)
    industry: str = Field(description="数字员工所处的行业信息")
    profile: Optional[dict[str, Any]] = Field(None, description="助理个人资料信息")

    @field_validator("assistant_name")
    def validate_assistant_name(cls, v):
        """验证助理姓名"""
        if not v or not v.strip():
            raise ValueError("助理姓名不能为空")
        return v.strip()

    @model_validator(mode='after')
    def validate_voice_config(self):
        """验证语音配置：voice_id 和 voice_file 至少需要提供一个"""
        if self.voice_id is None and self.voice_file is None:
            raise ValueError("voice_id 和 voice_file 至少需要提供一个")
        return self


class AssistantUpdateRequest(BaseModel):
    """
    更新AI员工请求模型
    """

    tenant_id: str = Field(description="租户标识符")
    assistant_name: Optional[str] = Field(None, description="助理姓名", min_length=1, max_length=100)
    nickname: Optional[str] = Field(None, description="助理昵称", max_length=100)
    address: Optional[str] = Field(None, description="助理地址", max_length=500)
    sex: Optional[str] = Field(None, description="助理性别", max_length=32)
    personality: Optional[str] = Field(None, description="助理个性类型")
    occupation: Optional[str] = Field(None, description="数字员工职业")
    voice_id: Optional[str] = Field(None, description="语音克隆配置")
    voice_file: Optional[str] = Field(None, description="语音文件URL链接", max_length=1024)
    industry: Optional[str] = Field(None, description="数字员工所在行业信息")
    profile: Optional[dict[str, Any]] = Field(None, description="助理个人资料信息")
    status: Optional[AccountStatus] = Field(None, description="助理状态")


# 响应模型
class AssistantDeleteResponse(BaseModel):
    """
    删除助理响应模型
    """
    is_delete: bool = Field(description="是否有删除操作")
