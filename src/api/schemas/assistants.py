"""
销售助理管理相关数据模型

该模块定义了销售助理管理相关的请求和响应数据模型，支持助理的创建、
配置、查询和管理等完整生命周期。

核心模型:
- AssistantCreateRequest: 创建助理请求
- AssistantUpdateRequest: 更新助理请求
- AssistantConfigRequest: 助理配置请求
- AssistantResponse: 助理响应
- AssistantListResponse: 助理列表响应
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from .requests import BaseRequest
from .responses import SuccessResponse, PaginatedResponse
from .prompts import AssistantPromptConfig


class AssistantStatus(str, Enum):
    """助理状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    TRAINING = "training"


class PersonalityType(str, Enum):
    """助理个性类型枚举"""
    PROFESSIONAL = "professional"      # 专业型
    FRIENDLY = "friendly"              # 友好型
    CONSULTATIVE = "consultative"      # 咨询型
    ENTHUSIASTIC = "enthusiastic"      # 热情型
    GENTLE = "gentle"                  # 温和型


class ExpertiseLevel(str, Enum):
    """专业等级枚举"""
    JUNIOR = "junior"                  # 初级
    INTERMEDIATE = "intermediate"      # 中级
    SENIOR = "senior"                  # 高级
    EXPERT = "expert"                  # 专家


class AssistantCreateRequest(BaseRequest):
    """
    创建销售助理请求模型
    """
    
    tenant_id: str = Field(
        description="租户标识符",
        min_length=1,
        max_length=100
    )
    
    assistant_name: str = Field(
        description="助理姓名",
        min_length=1,
        max_length=100
    )
    
    assistant_id: str = Field(
        description="助理唯一标识符",
        min_length=1,
        max_length=100
    )
    
    # 助理配置
    personality_type: PersonalityType = Field(
        default=PersonalityType.PROFESSIONAL,
        description="助理个性类型（可选，优先使用prompt_config）"
    )
    
    expertise_level: ExpertiseLevel = Field(
        default=ExpertiseLevel.INTERMEDIATE,
        description="专业等级"
    )
    
    # 提示词配置（新的核心配置）
    prompt_config: Optional[AssistantPromptConfig] = Field(
        None,
        description="智能体提示词配置 - 定义个性、行为和交互方式"
    )
    
    # 销售配置（保持向后兼容）
    sales_style: Dict[str, Any] = Field(
        default_factory=dict,
        description="销售风格配置（可选，建议使用prompt_config）"
    )
    
    voice_tone: Dict[str, Any] = Field(
        default_factory=dict,
        description="语音语调配置（可选，建议使用prompt_config）"
    )
    
    # 专业领域
    specializations: List[str] = Field(
        default_factory=list,
        description="专业领域列表（如：护肤、彩妆、香水等）"
    )
    
    # 工作配置
    working_hours: Dict[str, Any] = Field(
        default_factory=dict,
        description="工作时间配置"
    )
    
    max_concurrent_customers: int = Field(
        default=10,
        description="最大并发客户数",
        ge=1,
        le=100
    )
    
    # 权限配置
    permissions: List[str] = Field(
        default_factory=list,
        description="助理权限列表"
    )
    
    # 个人资料
    profile: Optional[Dict[str, Any]] = Field(
        None,
        description="助理个人资料信息"
    )
    
    @validator('assistant_id')
    def validate_assistant_id(cls, v):
        """验证助理ID格式"""
        if not v or not v.strip():
            raise ValueError('助理ID不能为空')
        if ' ' in v:
            raise ValueError('助理ID不能包含空格')
        return v.strip().lower()
    
    @validator('assistant_name')
    def validate_assistant_name(cls, v):
        """验证助理姓名"""
        if not v or not v.strip():
            raise ValueError('助理姓名不能为空')
        return v.strip()


class AssistantUpdateRequest(BaseRequest):
    """
    更新销售助理请求模型
    """
    
    assistant_name: Optional[str] = Field(
        None,
        description="助理姓名",
        min_length=1,
        max_length=100
    )
    
    personality_type: Optional[PersonalityType] = Field(
        None,
        description="助理个性类型"
    )
    
    expertise_level: Optional[ExpertiseLevel] = Field(
        None,
        description="专业等级"
    )
    
    # 提示词配置更新
    prompt_config: Optional[AssistantPromptConfig] = Field(
        None,
        description="智能体提示词配置更新"
    )
    
    sales_style: Optional[Dict[str, Any]] = Field(
        None,
        description="销售风格配置"
    )
    
    voice_tone: Optional[Dict[str, Any]] = Field(
        None,
        description="语音语调配置"
    )
    
    specializations: Optional[List[str]] = Field(
        None,
        description="专业领域列表"
    )
    
    working_hours: Optional[Dict[str, Any]] = Field(
        None,
        description="工作时间配置"
    )
    
    max_concurrent_customers: Optional[int] = Field(
        None,
        description="最大并发客户数",
        ge=1,
        le=100
    )
    
    permissions: Optional[List[str]] = Field(
        None,
        description="助理权限列表"
    )
    
    profile: Optional[Dict[str, Any]] = Field(
        None,
        description="助理个人资料信息"
    )
    
    status: Optional[AssistantStatus] = Field(
        None,
        description="助理状态"
    )


class AssistantConfigRequest(BaseRequest):
    """
    助理配置请求模型
    """
    
    config_type: str = Field(
        description="配置类型",
        regex="^(sales_style|voice_tone|working_hours|permissions|specializations)$"
    )
    
    config_data: Dict[str, Any] = Field(
        description="配置数据"
    )
    
    merge_mode: bool = Field(
        default=True,
        description="是否合并模式（True=合并，False=替换）"
    )


class AssistantListRequest(BaseRequest):
    """
    助理列表查询请求模型
    """
    
    tenant_id: str = Field(description="租户ID")
    
    # 筛选条件
    status: Optional[AssistantStatus] = Field(None, description="助理状态")
    personality_type: Optional[PersonalityType] = Field(None, description="个性类型")
    expertise_level: Optional[ExpertiseLevel] = Field(None, description="专业等级")
    specialization: Optional[str] = Field(None, description="专业领域筛选")
    
    # 搜索
    search: Optional[str] = Field(
        None,
        description="搜索关键词（姓名、ID）",
        max_length=100
    )
    
    # 排序
    sort_by: str = Field(
        default="created_at",
        description="排序字段",
        regex="^(created_at|assistant_name|expertise_level|status)$"
    )
    
    sort_order: str = Field(
        default="desc",
        description="排序方向",
        regex="^(asc|desc)$"
    )
    
    # 分页参数继承自BaseRequest
    include_stats: bool = Field(False, description="是否包含统计信息")
    include_config: bool = Field(False, description="是否包含详细配置")


# 响应模型

class AssistantResponse(SuccessResponse[Dict[str, Any]]):
    """
    销售助理响应模型
    """
    
    assistant_id: str = Field(description="助理ID")
    assistant_name: str = Field(description="助理姓名")
    tenant_id: str = Field(description="租户ID")
    
    # 基本信息
    status: AssistantStatus = Field(description="助理状态")
    personality_type: PersonalityType = Field(description="个性类型")
    expertise_level: ExpertiseLevel = Field(description="专业等级")
    
    # 配置信息
    sales_style: Dict[str, Any] = Field(
        default_factory=dict,
        description="销售风格配置"
    )
    
    voice_tone: Dict[str, Any] = Field(
        default_factory=dict,
        description="语音语调配置"
    )
    
    specializations: List[str] = Field(
        default_factory=list,
        description="专业领域列表"
    )
    
    working_hours: Dict[str, Any] = Field(
        default_factory=dict,
        description="工作时间配置"
    )
    
    max_concurrent_customers: int = Field(description="最大并发客户数")
    
    permissions: List[str] = Field(
        default_factory=list,
        description="助理权限列表"
    )
    
    # 统计信息
    current_customers: Optional[int] = Field(None, description="当前服务客户数")
    total_conversations: Optional[int] = Field(None, description="总对话数")
    average_rating: Optional[float] = Field(None, description="平均评分")
    
    # 时间信息
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
    last_active_at: Optional[datetime] = Field(None, description="最后活跃时间")
    
    # 设备信息
    registered_devices: Optional[List[str]] = Field(
        None,
        description="已注册设备ID列表"
    )


class AssistantListResponse(PaginatedResponse[List[Dict[str, Any]]]):
    """
    助理列表响应模型
    """
    
    assistants: List[Dict[str, Any]] = Field(description="助理列表")
    
    # 聚合统计
    total_assistants: int = Field(description="总助理数")
    active_assistants: int = Field(description="活跃助理数")
    
    # 统计摘要
    status_distribution: Dict[str, int] = Field(description="状态分布")
    expertise_distribution: Dict[str, int] = Field(description="专业等级分布")
    
    # 过滤统计
    filter_summary: Dict[str, int] = Field(description="过滤条件统计")


class AssistantStatsResponse(SuccessResponse[Dict[str, Any]]):
    """
    助理统计响应模型
    """
    
    assistant_id: str = Field(description="助理ID")
    
    # 基础统计
    total_conversations: int = Field(description="总对话数")
    total_customers: int = Field(description="总客户数")
    active_conversations: int = Field(description="活跃对话数")
    
    # 性能指标
    average_response_time: float = Field(description="平均响应时间（秒）")
    customer_satisfaction: float = Field(description="客户满意度")
    conversion_rate: float = Field(description="转化率")
    
    # 时间分布
    activity_by_hour: Dict[str, int] = Field(description="按小时活动分布")
    activity_by_day: Dict[str, int] = Field(description="按日活动分布")
    
    # 设备统计
    device_usage: Dict[str, Dict[str, Any]] = Field(
        description="设备使用统计"
    )
    
    # 趋势数据
    trends: Dict[str, List[float]] = Field(description="趋势数据")


class AssistantOperationResponse(SuccessResponse[Dict[str, Any]]):
    """
    助理操作响应模型
    """
    
    assistant_id: str = Field(description="助理ID")
    operation: str = Field(description="执行的操作")
    success: bool = Field(description="操作是否成功")
    
    # 操作结果
    result_data: Optional[Dict[str, Any]] = Field(
        None,
        description="操作结果数据"
    )
    
    # 状态变更
    previous_status: Optional[str] = Field(None, description="操作前状态")
    new_status: Optional[str] = Field(None, description="操作后状态")
    
    # 影响统计
    affected_conversations: Optional[int] = Field(
        None,
        description="受影响的对话数"
    )
    
    affected_devices: Optional[int] = Field(
        None,
        description="受影响的设备数"
    )