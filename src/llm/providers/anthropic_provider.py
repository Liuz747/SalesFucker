"""
Anthropic Claude供应商实现模块

该模块实现了Anthropic Claude LLM供应商的具体功能，包括Claude系列模型的调用、
流式响应处理和中文优化。Claude在推理和安全性方面表现优异。

核心功能:
- Claude-3.5-Sonnet、Claude-3-Haiku 等模型支持
- 流式和非流式响应处理
- 中文语言优化和文化适应
- 安全性和合规性增强
- 成本追踪和使用统计
"""

from typing import Dict, Any, Optional, List, AsyncGenerator
import anthropic
from anthropic import AsyncAnthropic
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


class AnthropicProvider(BaseProvider):
    """
    Anthropic Claude供应商实现类
    
    提供Claude系列模型的完整支持，特别优化了中文处理和安全性。
    Claude在复杂推理、内容审核和创意写作方面表现优异。
    """
    
    def __init__(self, config: ProviderConfig):
        """
        初始化Anthropic供应商
        
        参数:
            config: Anthropic供应商配置
        """
        super().__init__(config)
        
        # 初始化Anthropic客户端
        self.client = AsyncAnthropic(
            api_key=config.credentials.api_key,
            base_url=config.credentials.api_base,
            timeout=config.timeout_seconds
        )
        
        # Claude模型定价(每1K tokens)
        self.pricing = {
            "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
            "claude-3-5-haiku-20241022": {"input": 0.00025, "output": 0.00125},
            "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
            "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125}
        }
        
        # 中文优化系统提示
        self.chinese_system_prompt = """你是一个专业的中文AI助手，擅长理解中文语境和文化背景。
请用自然、地道的中文回答问题，注意：
1. 使用符合中文表达习惯的语言
2. 理解中文的语境和隐含意义  
3. 考虑中国文化背景和价值观
4. 保持回答的准确性和专业性
5. 根据对话场景调整语言风格"""
        
        self.logger.info("Anthropic Claude供应商初始化完成")
    
    async def _make_request(self, request: LLMRequest) -> LLMResponse:
        """
        执行Anthropic Claude API请求
        
        参数:
            request: LLM请求对象
            
        返回:
            LLMResponse: API响应对象
        """
        try:
            start_time = time.time()
            
            # 构建请求参数
            api_params = self._build_api_params(request)
            
            # 调用Claude API
            response = await self.client.messages.create(**api_params)
            
            # 处理响应
            content = self._extract_content(response)
            usage_tokens = response.usage.input_tokens + response.usage.output_tokens
            model_used = response.model
            
            # 计算成本
            cost = self._calculate_cost(model_used, response.usage)
            
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
                    "stop_reason": response.stop_reason,
                    "usage_details": {
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens
                    }
                }
            )
            
        except anthropic.RateLimitError as e:
            raise RateLimitError(str(e), self.provider_type, "ANTHROPIC_RATE_LIMIT")
        except anthropic.AuthenticationError as e:
            raise AuthenticationError(str(e), self.provider_type, "ANTHROPIC_AUTH_ERROR")
        except anthropic.NotFoundError as e:
            raise ModelNotFoundError(str(e), self.provider_type, "ANTHROPIC_MODEL_NOT_FOUND")
        except Exception as e:
            raise ProviderError(f"Anthropic API错误: {str(e)}", self.provider_type, "ANTHROPIC_API_ERROR")
    
    async def _handle_streaming(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """
        处理Claude流式响应
        
        参数:
            request: LLM请求对象
            
        生成:
            str: 流式响应内容片段
        """
        try:
            # 构建流式请求参数
            api_params = self._build_api_params(request)
            
            # 创建流式请求
            async with self.client.messages.stream(**api_params) as stream:
                async for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            self.logger.error(f"Claude流式处理错误: {str(e)}")
            raise ProviderError(f"流式处理失败: {str(e)}", self.provider_type, "STREAMING_ERROR")
    
    def _build_api_params(self, request: LLMRequest) -> Dict[str, Any]:
        """
        构建Claude API请求参数
        
        参数:
            request: LLM请求对象
            
        返回:
            Dict[str, Any]: API请求参数
        """
        # 获取模型配置
        model = request.model or self._get_default_model(request)
        model_config = self.config.models.get(model, {})
        
        # 构建消息和系统提示
        messages, system_prompt = self._format_messages(request.messages)
        
        params = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens or model_config.get("max_tokens", 4096),
            "temperature": request.temperature or model_config.get("temperature", 0.7)
        }
        
        # 添加系统提示
        if system_prompt:
            params["system"] = system_prompt
        
        return params
    
    def _format_messages(self, messages: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], str]:
        """
        格式化消息为Claude格式
        
        Claude要求系统消息单独处理，用户和助手消息交替出现。
        
        参数:
            messages: 原始消息列表
            
        返回:
            tuple: (格式化消息列表, 系统提示)
        """
        formatted_messages = []
        system_prompt = ""
        
        # 检查是否包含中文内容
        is_chinese = self._is_chinese_content(messages)
        
        for msg in messages:
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                # 处理系统消息
                if role == "system":
                    system_prompt = content
                    # 如果是中文内容，添加中文优化提示
                    if is_chinese and not system_prompt:
                        system_prompt = self.chinese_system_prompt
                    elif is_chinese:
                        system_prompt = f"{self.chinese_system_prompt}\n\n{content}"
                # 处理用户和助手消息
                elif role in ["user", "assistant"]:
                    formatted_messages.append({
                        "role": role,
                        "content": content
                    })
        
        # 如果没有系统提示但内容是中文，添加默认中文优化提示
        if not system_prompt and is_chinese:
            system_prompt = self.chinese_system_prompt
        
        # 确保消息交替(Claude要求)
        formatted_messages = self._ensure_alternating_roles(formatted_messages)
        
        return formatted_messages, system_prompt
    
    def _ensure_alternating_roles(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        确保消息角色交替(Claude API要求)
        
        参数:
            messages: 消息列表
            
        返回:
            List[Dict[str, Any]]: 角色交替的消息列表
        """
        if not messages:
            return messages
        
        result = []
        last_role = None
        
        for msg in messages:
            current_role = msg["role"]
            
            # 如果角色重复，合并消息内容
            if current_role == last_role and result:
                result[-1]["content"] += f"\n\n{msg['content']}"
            else:
                result.append(msg)
                last_role = current_role
        
        # 确保以用户消息开始
        if result and result[0]["role"] != "user":
            result.insert(0, {"role": "user", "content": "请继续我们的对话。"})
        
        return result
    
    def _extract_content(self, response) -> str:
        """
        提取Claude响应内容
        
        参数:
            response: Claude API响应对象
            
        返回:
            str: 响应文本内容
        """
        if hasattr(response, 'content') and response.content:
            # Claude响应是列表格式
            content_blocks = response.content
            text_content = []
            
            for block in content_blocks:
                if hasattr(block, 'text'):
                    text_content.append(block.text)
            
            return "".join(text_content)
        
        return ""
    
    def _get_default_model(self, request: LLMRequest) -> str:
        """
        根据请求类型获取默认Claude模型
        
        参数:
            request: LLM请求对象
            
        返回:
            str: 默认模型名称
        """
        # 根据智能体类型选择模型
        agent_type = request.agent_type
        
        if agent_type == "compliance":
            return "claude-3-5-sonnet-20241022"  # 最佳安全性分析
        elif agent_type in ["sentiment", "intent"]:
            return "claude-3-5-sonnet-20241022"  # 优秀的情感理解
        elif agent_type in ["sales", "product"]:
            return "claude-3-5-sonnet-20241022"  # 强推理能力
        else:
            return "claude-3-5-haiku-20241022"  # 快速响应
    
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
    
    def _calculate_cost(self, model: str, usage) -> float:
        """
        计算请求成本
        
        参数:
            model: 使用的模型
            usage: 使用详情对象
            
        返回:
            float: 请求成本(美元)
        """
        if model not in self.pricing:
            # 使用默认价格
            total_tokens = usage.input_tokens + usage.output_tokens
            return total_tokens * 0.003 / 1000
        
        pricing = self.pricing[model]
        
        # Claude提供精确的输入输出令牌计数
        input_cost = (usage.input_tokens / 1000) * pricing["input"]
        output_cost = (usage.output_tokens / 1000) * pricing["output"]
        
        return input_cost + output_cost
    
    async def get_available_models(self) -> List[ModelConfig]:
        """
        获取Claude可用模型列表
        
        返回:
            List[ModelConfig]: 可用模型配置列表
        """
        models = [
            ModelConfig(
                model_name="claude-3-5-sonnet-20241022",
                display_name="Claude 3.5 Sonnet",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.REASONING,
                    ModelCapability.CHINESE_OPTIMIZATION,
                    ModelCapability.CODE_GENERATION
                ],
                max_tokens=8192,
                cost_per_1k_tokens=0.009,
                supports_chinese=True
            ),
            ModelConfig(
                model_name="claude-3-5-haiku-20241022",
                display_name="Claude 3.5 Haiku",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.FAST_RESPONSE,
                    ModelCapability.COST_EFFECTIVE,
                    ModelCapability.CHINESE_OPTIMIZATION
                ],
                max_tokens=8192,
                cost_per_1k_tokens=0.000625,
                supports_chinese=True
            ),
            ModelConfig(
                model_name="claude-3-opus-20240229",
                display_name="Claude 3 Opus",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.REASONING,
                    ModelCapability.CHINESE_OPTIMIZATION,
                    ModelCapability.CODE_GENERATION
                ],
                max_tokens=4096,
                cost_per_1k_tokens=0.045,
                supports_chinese=True
            ),
            ModelConfig(
                model_name="claude-3-sonnet-20240229",
                display_name="Claude 3 Sonnet",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.REASONING,
                    ModelCapability.CHINESE_OPTIMIZATION
                ],
                max_tokens=4096,
                cost_per_1k_tokens=0.009,
                supports_chinese=True
            )
        ]
        
        return models
    
    async def test_connection(self) -> bool:
        """
        测试Anthropic连接
        
        返回:
            bool: 连接是否成功
        """
        try:
            # 发送简单的测试请求
            response = await self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}]
            )
            return True
        except Exception as e:
            self.logger.error(f"Anthropic连接测试失败: {str(e)}")
            return False