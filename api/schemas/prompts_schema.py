"""
智能体提示词管理数据模型

该模块定义了提示词管理相关的数据模型，支持基于提示词的智能体
个性化定制，实现更灵活和精确的客户交互控制。

核心模型:
- PromptTemplate: 提示词模板
- AssistantPromptConfig: 智能体提示词配置
- PromptTestRequest: 提示词测试请求
- PromptLibraryItem: 提示词库项目
"""
from typing import Any, Dict, List, Optional

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator



class PromptType(str, Enum):
    """提示词类型枚举"""

    SYSTEM = "system"  # 系统提示词
    PERSONALITY = "personality"  # 个性化提示词
    GREETING = "greeting"  # 问候提示词
    PRODUCT = "product"  # 产品推荐提示词
    CLOSING = "closing"  # 结束对话提示词
    OBJECTION = "objection"  # 异议处理提示词
    FOLLOWUP = "followup"  # 跟进提示词


class PromptCategory(str, Enum):
    """提示词分类枚举"""

    SALES = "sales"  # 销售相关
    CUSTOMER_SERVICE = "customer_service"  # 客户服务
    CONSULTATION = "consultation"  # 咨询建议
    EDUCATION = "education"  # 教育科普
    ENTERTAINMENT = "entertainment"  # 娱乐互动


class PromptLanguage(str, Enum):
    """支持的语言枚举"""

    CHINESE = "zh"  # 中文
    ENGLISH = "en"  # 英文
    JAPANESE = "ja"  # 日文
    KOREAN = "ko"  # 韩文


class PromptTemplate(BaseModel):
    """
    提示词模板模型
    """

    template_id: str = Field(description="模板唯一标识符")
    template_name: str = Field(description="模板名称", min_length=1, max_length=100)
    template_type: PromptType = Field(description="提示词类型")
    category: PromptCategory = Field(description="提示词分类")
    language: PromptLanguage = Field(default=PromptLanguage.CHINESE, description="语言")

    # 提示词内容
    system_prompt: str = Field(
        description="系统级提示词", min_length=1, max_length=4000
    )
    user_prompt_template: Optional[str] = Field(
        None, description="用户提示词模板（支持变量替换）", max_length=2000
    )

    # 变量定义
    variables: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="提示词变量定义 {变量名: {type, description, default, required}}",
    )

    # 配置参数
    temperature: float = Field(default=0.7, description="LLM温度参数", ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(
        default=1000, description="最大生成token数", ge=1, le=4000
    )

    # 元数据
    description: Optional[str] = Field(None, description="模板描述", max_length=500)
    tags: List[str] = Field(default_factory=list, description="标签列表")
    usage_instructions: Optional[str] = Field(
        None, description="使用说明", max_length=1000
    )

    # 示例
    example_inputs: Optional[List[Dict[str, Any]]] = Field(
        None, description="输入示例列表"
    )
    expected_outputs: Optional[List[str]] = Field(None, description="预期输出示例")

    @field_validator("variables")
    def validate_variables(cls, v):
        """验证变量定义格式"""
        for var_name, var_config in v.items():
            if not isinstance(var_config, dict):
                raise ValueError(f"变量 {var_name} 配置必须是字典格式")

            required_keys = {"type", "description"}
            if not required_keys.issubset(var_config.keys()):
                raise ValueError(f"变量 {var_name} 必须包含 {required_keys} 键")

        return v


class AssistantPromptConfig(BaseModel):
    """
    智能体提示词配置模型
    """

    # 基础配置
    assistant_id: str = Field(description="智能体ID")
    tenant_id: str = Field(description="租户ID")

    # 主要提示词配置
    personality_prompt: str = Field(
        description="个性化系统提示词 - 定义智能体性格、语调、行为方式",
        min_length=50,
        max_length=4000,
    )

    # 分场景提示词
    greeting_prompt: Optional[str] = Field(
        None, description="问候提示词 - 定义如何开始对话", max_length=500
    )

    product_recommendation_prompt: Optional[str] = Field(
        None, description="产品推荐提示词 - 定义如何推荐产品", max_length=1000
    )

    objection_handling_prompt: Optional[str] = Field(
        None, description="异议处理提示词 - 定义如何处理客户异议", max_length=1000
    )

    closing_prompt: Optional[str] = Field(
        None, description="结束对话提示词 - 定义如何结束对话", max_length=500
    )

    # 上下文配置
    context_instructions: Optional[str] = Field(
        None, description="上下文处理指令 - 如何利用历史对话和客户信息", max_length=1000
    )

    # LLM参数配置
    llm_parameters: Dict[str, Any] = Field(
        default_factory=lambda: {
            "temperature": 0.7,
            "max_tokens": 1000,
            "top_p": 0.9,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        },
        description="LLM生成参数配置",
    )

    # 安全和合规
    safety_guidelines: List[str] = Field(
        default_factory=list, description="安全和合规指导原则"
    )

    forbidden_topics: List[str] = Field(
        default_factory=list, description="禁止讨论的话题列表"
    )

    # 品牌和产品信息
    brand_voice: Optional[str] = Field(
        None, description="品牌声音定义 - 品牌特色和价值观", max_length=500
    )

    product_knowledge: Optional[str] = Field(
        None, description="产品知识要点 - 重点产品信息和卖点", max_length=2000
    )

    # 版本控制
    # version: str = Field(default="1.0.0", description="配置版本")
    # 版本控制目前使用 时间戳，暂不支持用户自定义

    is_active: bool = Field(default=True, description="是否启用")

    @field_validator("llm_parameters")
    def validate_llm_parameters(cls, v):
        """验证LLM参数"""
        if "temperature" in v and not 0.0 <= v["temperature"] <= 2.0:
            raise ValueError("temperature参数必须在0.0-2.0之间")
        if "max_tokens" in v and not 1 <= v["max_tokens"] <= 4000:
            raise ValueError("max_tokens参数必须在1-4000之间")
        return v


class PromptTestRequest(BaseModel):
    """
    提示词测试请求模型
    """

    # 测试配置
    prompt_config: AssistantPromptConfig = Field(description="要测试的提示词配置")

    # 测试场景
    test_scenarios: List[Dict[str, Any]] = Field(
        description="测试场景列表", min_items=1, max_items=10
    )

    # 测试参数
    llm_provider: Optional[str] = Field(None, description="指定LLM提供商")
    model_name: Optional[str] = Field(None, description="指定模型名称")

    # 评估标准
    evaluation_criteria: Optional[Dict[str, Any]] = Field(
        None, description="评估标准配置"
    )

    @field_validator("test_scenarios")
    def validate_test_scenarios(cls, v):
        """验证测试场景"""
        for scenario in v:
            if "input" not in scenario:
                raise ValueError("每个测试场景必须包含 'input' 字段")
            if "context" not in scenario:
                scenario["context"] = {}
        return v


class PromptLibraryItem(BaseModel):
    """
    提示词库项目模型
    """

    item_id: str = Field(description="库项目ID")
    title: str = Field(description="标题", min_length=1, max_length=100)
    category: PromptCategory = Field(description="分类")
    prompt_type: PromptType = Field(description="提示词类型")
    language: PromptLanguage = Field(description="语言")

    # 内容
    prompt_content: str = Field(description="提示词内容", min_length=1, max_length=4000)
    use_case: str = Field(description="使用场景描述", max_length=500)

    # 配置建议
    recommended_parameters: Dict[str, Any] = Field(
        default_factory=dict, description="推荐的LLM参数配置"
    )

    # 元数据
    author: Optional[str] = Field(None, description="作者")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="更新时间"
    )
    usage_count: int = Field(default=0, description="使用次数")
    rating: float = Field(default=0.0, description="评分", ge=0.0, le=5.0)

    # 示例和说明
    example_context: Optional[Dict[str, Any]] = Field(None, description="示例上下文")
    example_output: Optional[str] = Field(None, description="示例输出")
    notes: Optional[str] = Field(None, description="使用注意事项", max_length=500)


# 请求模型


class PromptCreateRequest(BaseModel):
    """创建提示词配置请求"""

    assistant_id: str = Field(description="智能体ID")
    tenant_id: str = Field(description="租户ID")
    prompt_config: AssistantPromptConfig = Field(description="提示词配置")


class PromptUpdateRequest(BaseModel):
    """更新提示词配置请求"""

    # 可选更新字段
    personality_prompt: Optional[str] = Field(None, description="个性化提示词")
    greeting_prompt: Optional[str] = Field(None, description="问候提示词")
    product_recommendation_prompt: Optional[str] = Field(
        None, description="产品推荐提示词"
    )
    objection_handling_prompt: Optional[str] = Field(None, description="异议处理提示词")
    closing_prompt: Optional[str] = Field(None, description="结束对话提示词")
    context_instructions: Optional[str] = Field(None, description="上下文处理指令")
    llm_parameters: Optional[Dict[str, Any]] = Field(None, description="LLM参数")
    brand_voice: Optional[str] = Field(None, description="品牌声音")
    product_knowledge: Optional[str] = Field(None, description="产品知识")
    safety_guidelines: Optional[List[str]] = Field(None, description="安全指导原则")
    forbidden_topics: Optional[List[str]] = Field(None, description="禁止话题")
    is_active: Optional[bool] = Field(None, description="是否启用")


class PromptLibrarySearchRequest(BaseModel):
    """提示词库搜索请求"""

    category: Optional[PromptCategory] = Field(None, description="分类筛选")
    prompt_type: Optional[PromptType] = Field(None, description="类型筛选")
    language: Optional[PromptLanguage] = Field(None, description="语言筛选")
    search_text: Optional[str] = Field(None, description="搜索关键词")
    sort_by: str = Field(default="rating", description="排序字段")
    sort_order: str = Field(default="desc", description="排序方向")
    page: int = Field(1, ge=1, description="页码，从1开始")
    page_size: int = Field(20, ge=1, le=100, description="每页大小，最大100")


# 响应模型

class PromptConfigResponse(BaseModel):
    """提示词配置响应"""

    assistant_id: str = Field(description="智能体ID")
    tenant_id: str = Field(description="租户ID")
    config: AssistantPromptConfig = Field(description="提示词配置")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")



class PromptTestResponse(BaseModel):
    """提示词测试响应"""

    test_id: str = Field(description="测试ID")
    test_results: List[Dict[str, Any]] = Field(description="测试结果列表")
    overall_score: float = Field(description="总体评分")
    recommendations: List[str] = Field(description="优化建议")
    performance_metrics: Dict[str, Any] = Field(description="性能指标")


class PromptLibraryResponse(BaseModel):
    """提示词库响应"""

    # page: int = Field(description="分页信息")
    # page_size: int = Field(description="分页信息")
    # pages: int = Field(description="分页信息")
    items: List[PromptLibraryItem] = Field(description="提示词库项目列表")
    categories: Dict[str, int] = Field(description="分类统计")
    languages: Dict[str, int] = Field(description="语言统计")


class PromptValidationResponse(BaseModel):
    """提示词验证响应"""

    is_valid: bool = Field(description="是否有效")
    validation_results: Dict[str, Any] = Field(description="验证结果详情")
    suggestions: List[str] = Field(description="改进建议")
    estimated_performance: Dict[str, float] = Field(description="预估性能指标")
