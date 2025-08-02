"""
OpenAI供应商实现模块

该模块实现了OpenAI LLM供应商的具体功能，包括GPT系列模型的调用、
流式响应处理、多模态支持和中文优化。

核心功能:
- GPT-4、GPT-3.5 等模型支持
- 流式和非流式响应处理
- 图像分析(GPT-4V)支持
- 中文语言优化
- 成本追踪和使用统计
"""

from typing import Dict, Any, Optional, List, AsyncGenerator
import openai
from openai import AsyncOpenAI
import json
import time

from ..base_provider import (
    BaseProvider, 
    LLMRequest, 
    LLMResponse, 
    RequestType,
    ProviderError,
    RateLimitError,
    AuthenticationError,
    ModelNotFoundError
)
from ..provider_config import (
    ProviderType, 
    ProviderConfig, 
    ModelConfig,
    ModelCapability
)


class OpenAIProvider(BaseProvider):
    """
    OpenAI供应商实现类
    
    提供OpenAI GPT系列模型的完整支持，包括文本生成、
    多模态处理和流式响应等功能。
    """
    
    def __init__(self, config: ProviderConfig):
        """
        初始化OpenAI供应商
        
        参数:
            config: OpenAI供应商配置
        """
        super().__init__(config)
        
        # 初始化OpenAI客户端
        self.client = AsyncOpenAI(
            api_key=config.credentials.api_key,
            base_url=config.credentials.api_base,
            organization=config.credentials.organization,
            timeout=config.timeout_seconds
        )
        
        # OpenAI模型定价(每1K tokens)
        self.pricing = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-0125-preview": {"input": 0.01, "output": 0.03},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-4-vision-preview": {"input": 0.01, "output": 0.03},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004}
        }
        
        self.logger.info("OpenAI供应商初始化完成")
    
    async def _make_request(self, request: LLMRequest) -> LLMResponse:
        """
        执行OpenAI API请求
        
        参数:
            request: LLM请求对象
            
        返回:
            LLMResponse: API响应对象
        """
        try:
            start_time = time.time()
            
            # 构建请求参数
            api_params = self._build_api_params(request)
            
            # 调用OpenAI API
            if request.request_type == RequestType.CHAT_COMPLETION:
                response = await self.client.chat.completions.create(**api_params)
            else:
                raise ProviderError(
                    f"不支持的请求类型: {request.request_type}",
                    self.provider_type,
                    "UNSUPPORTED_REQUEST_TYPE"
                )
            
            # 处理响应
            content = response.choices[0].message.content or ""
            usage_tokens = response.usage.total_tokens if response.usage else 0
            model_used = response.model
            
            # 计算成本
            cost = self._calculate_cost(model_used, usage_tokens, response.usage)
            
            response_time = time.time() - start_time
            
            return LLMResponse(
                request_id=request.request_id,
                provider_type=self.provider_type,
                model=model_used,
                content=content,
                usage_tokens=usage_tokens,
                cost=cost,
                response_time=response_time,
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "usage_details": response.usage.dict() if response.usage else {}
                }
            )
            
        except openai.RateLimitError as e:
            raise RateLimitError(str(e), self.provider_type, "OPENAI_RATE_LIMIT")
        except openai.AuthenticationError as e:
            raise AuthenticationError(str(e), self.provider_type, "OPENAI_AUTH_ERROR")
        except openai.NotFoundError as e:
            raise ModelNotFoundError(str(e), self.provider_type, "OPENAI_MODEL_NOT_FOUND")
        except Exception as e:
            raise ProviderError(f"OpenAI API错误: {str(e)}", self.provider_type, "OPENAI_API_ERROR")
    
    async def _handle_streaming(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """
        处理OpenAI流式响应
        
        参数:
            request: LLM请求对象
            
        生成:
            str: 流式响应内容片段
        """
        try:
            # 构建流式请求参数
            api_params = self._build_api_params(request)
            api_params["stream"] = True
            
            # 创建流式请求
            stream = await self.client.chat.completions.create(**api_params)
            
            # 逐个处理响应块
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    yield content
                    
        except Exception as e:
            self.logger.error(f"流式处理错误: {str(e)}")
            raise ProviderError(f"流式处理失败: {str(e)}", self.provider_type, "STREAMING_ERROR")
    
    def _build_api_params(self, request: LLMRequest) -> Dict[str, Any]:
        """
        构建OpenAI API请求参数
        
        参数:
            request: LLM请求对象
            
        返回:
            Dict[str, Any]: API请求参数
        """
        # 获取模型配置
        model = request.model or self._get_default_model(request)
        model_config = self.config.models.get(model, {})
        
        params = {
            "model": model,
            "messages": self._format_messages(request.messages),
            "temperature": request.temperature or model_config.get("temperature", 0.7),
            "max_tokens": request.max_tokens or model_config.get("max_tokens", 4096)
        }
        
        # 中文优化提示
        if self._is_chinese_content(request.messages):
            params["temperature"] = min(params["temperature"], 0.3)  # 降低温度提高准确性
        
        return params
    
    def _format_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        格式化消息为OpenAI格式
        
        参数:
            messages: 原始消息列表
            
        返回:
            List[Dict[str, Any]]: 格式化后的消息列表
        """
        formatted_messages = []
        
        for msg in messages:
            if isinstance(msg, dict):
                # 处理文本消息
                if "content" in msg and "role" in msg:
                    formatted_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
                # 处理多模态消息(图像)
                elif "image_url" in msg:
                    formatted_messages.append({
                        "role": msg.get("role", "user"),
                        "content": [
                            {
                                "type": "text",
                                "text": msg.get("text", "分析这个图像")
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": msg["image_url"]}
                            }
                        ]
                    })
        
        return formatted_messages
    
    def _get_default_model(self, request: LLMRequest) -> str:
        """
        根据请求类型获取默认模型
        
        参数:
            request: LLM请求对象
            
        返回:
            str: 默认模型名称
        """
        # 检查是否包含图像
        has_image = any(
            "image_url" in msg if isinstance(msg, dict) else False 
            for msg in request.messages
        )
        
        if has_image:
            return "gpt-4-vision-preview"
        
        # 根据智能体类型选择模型
        agent_type = request.agent_type
        if agent_type in ["compliance", "sentiment", "intent"]:
            return "gpt-4-turbo"  # 高质量分析任务
        elif agent_type in ["sales", "product"]:
            return "gpt-4"  # 复杂推理任务
        else:
            return "gpt-3.5-turbo"  # 通用任务
    
    def _is_chinese_content(self, messages: List[Dict[str, Any]]) -> bool:
        """
        检测消息是否包含中文内容
        
        参数:
            messages: 消息列表
            
        返回:
            bool: 是否包含中文
        """
        chinese_chars = set('的一是在不了有和人这中大为上个国我以要他时来用们生到作地于出就分对成会可主发年动同工也能下过子说产种面而方后多定行学法所民得经十三之进着等部度家电力里如水化高自二理起小物现实加量都两体制机当使点从业本去把性好应开它合还因由其些然前外天政四日那社义事平形相全表间样与关各重新线内数正心反你明看原又么利比或但质气第向道命此变条只没结解问意建月公无系军很情者最立代想已通并提直题党程展五果料象员革位入常文总次品式活设及管特件长求老头基资边流路级少图山统接知较将组见计别她手角期根论运农指几九区强放决西被干做必战先回则任取据处队南给色光门即保治北造百规热领七海口东导器压志世金增争济阶油思术极交受联什认六共权收证改清己美再采转更单风切打白教速花带安场身车例真务具万每目至达走积示议声报斗完类八离华名确才科张信马节话米整空元况今集温传土许步群广石记需段研界拉林律叫且究观越织装影算低持音众书布复容儿须际商非验连断深难近矿千周委素技备半办青省列习响约支般史感劳便团往酸历市克何除消构府称太准精值号率族维划选标写存候毛亲快效斯院查江型眼王按格养易置派层片始却专状育厂京识适属圆包火住调满县局照参红细引听该铁价严')
        
        for msg in messages:
            if isinstance(msg, dict) and "content" in msg:
                content = str(msg["content"])
                if any(char in chinese_chars for char in content):
                    return True
        
        return False
    
    def _calculate_cost(self, model: str, total_tokens: int, usage: Any) -> float:
        """
        计算请求成本
        
        参数:
            model: 使用的模型
            total_tokens: 总令牌数
            usage: 使用详情对象
            
        返回:
            float: 请求成本(美元)
        """
        if model not in self.pricing:
            # 使用默认价格
            return total_tokens * 0.002 / 1000
        
        pricing = self.pricing[model]
        
        if usage and hasattr(usage, 'prompt_tokens') and hasattr(usage, 'completion_tokens'):
            # 精确计算
            input_cost = (usage.prompt_tokens / 1000) * pricing["input"]
            output_cost = (usage.completion_tokens / 1000) * pricing["output"]
            return input_cost + output_cost
        else:
            # 估算(假设输入输出各占一半)
            avg_price = (pricing["input"] + pricing["output"]) / 2
            return (total_tokens / 1000) * avg_price
    
    async def get_available_models(self) -> List[ModelConfig]:
        """
        获取OpenAI可用模型列表
        
        返回:
            List[ModelConfig]: 可用模型配置列表
        """
        models = [
            ModelConfig(
                model_name="gpt-4",
                display_name="GPT-4",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.REASONING,
                    ModelCapability.CHINESE_OPTIMIZATION
                ],
                max_tokens=8192,
                cost_per_1k_tokens=0.045,
                supports_chinese=True
            ),
            ModelConfig(
                model_name="gpt-4-turbo",
                display_name="GPT-4 Turbo",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.REASONING,
                    ModelCapability.CHINESE_OPTIMIZATION,
                    ModelCapability.FAST_RESPONSE
                ],
                max_tokens=128000,
                cost_per_1k_tokens=0.02,
                supports_chinese=True
            ),
            ModelConfig(
                model_name="gpt-4-vision-preview",
                display_name="GPT-4 Vision",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.MULTIMODAL,
                    ModelCapability.REASONING,
                    ModelCapability.CHINESE_OPTIMIZATION
                ],
                max_tokens=4096,
                cost_per_1k_tokens=0.02,
                supports_chinese=True
            ),
            ModelConfig(
                model_name="gpt-3.5-turbo",
                display_name="GPT-3.5 Turbo",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.FAST_RESPONSE,
                    ModelCapability.COST_EFFECTIVE,
                    ModelCapability.CHINESE_OPTIMIZATION
                ],
                max_tokens=16384,
                cost_per_1k_tokens=0.001,
                supports_chinese=True
            )
        ]
        
        return models
    
    async def test_connection(self) -> bool:
        """
        测试OpenAI连接
        
        返回:
            bool: 连接是否成功
        """
        try:
            await self.client.models.list()
            return True
        except Exception as e:
            self.logger.error(f"OpenAI连接测试失败: {str(e)}")
            return False