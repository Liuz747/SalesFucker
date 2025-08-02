"""
DeepSeek供应商实现模块

该模块实现了DeepSeek LLM供应商的具体功能，使用OpenAI兼容接口。
DeepSeek在中文处理和代码生成方面表现优异，具有极高的性价比。

核心功能:
- DeepSeek-V2、DeepSeek-Coder 等模型支持
- 使用OpenAI兼容接口简化集成
- 专业的中文语言处理和理解
- 优秀的代码生成能力
- 极高性价比的定价策略
"""

from typing import Dict, Any, Optional, List, AsyncGenerator
from openai import AsyncOpenAI
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


class DeepSeekProvider(BaseProvider):
    """
    DeepSeek供应商实现类
    
    通过OpenAI兼容接口提供DeepSeek模型支持。DeepSeek在中文处理、
    数学推理和代码生成方面表现优异，同时具有极高的性价比。
    """
    
    def __init__(self, config: ProviderConfig):
        """
        初始化DeepSeek供应商
        
        参数:
            config: DeepSeek供应商配置
        """
        super().__init__(config)
        
        # 初始化DeepSeek客户端(使用OpenAI兼容接口)
        base_url = config.credentials.api_base or "https://api.deepseek.com/v1"
        
        self.client = AsyncOpenAI(
            api_key=config.credentials.api_key,
            base_url=base_url,
            timeout=config.timeout_seconds
        )
        
        # DeepSeek模型定价(每1K tokens) - 极高性价比
        self.pricing = {
            "deepseek-chat": {"input": 0.00014, "output": 0.00028},
            "deepseek-coder": {"input": 0.00014, "output": 0.00028},
            "deepseek-v2": {"input": 0.00014, "output": 0.00028}
        }
        
        # 中文优化系统提示
        self.chinese_system_prompt = """你是一个专业的中文AI助手，专门为中国用户提供服务。请注意：

1. 语言风格：使用自然流畅的现代汉语，符合中国大陆的语言习惯
2. 文化理解：理解中国文化背景、社会现象和价值观念
3. 本土化：提供符合中国国情的建议和解决方案
4. 专业性：在保持通俗易懂的同时确保内容的准确性和专业性
5. 实用性：提供实际可行的建议和具体的操作指导

请根据用户的具体需求，提供有针对性的、高质量的中文回答。"""
        
        # 代码生成优化提示
        self.code_system_prompt = """你是一个专业的编程助手，擅长多种编程语言。请注意：

1. 代码质量：编写清晰、高效、可维护的代码
2. 注释说明：为关键逻辑添加中文注释
3. 最佳实践：遵循相应语言的编码规范和最佳实践
4. 错误处理：考虑异常情况并提供适当的错误处理
5. 性能优化：在保证可读性的前提下优化代码性能

如果用户提出编程相关问题，请提供完整、可运行的代码示例。"""
        
        self.logger.info("DeepSeek供应商初始化完成")
    
    async def _make_request(self, request: LLMRequest) -> LLMResponse:
        """
        执行DeepSeek API请求
        
        参数:
            request: LLM请求对象
            
        返回:
            LLMResponse: API响应对象
        """
        try:
            start_time = time.time()
            
            # 构建请求参数
            api_params = self._build_api_params(request)
            
            # 调用DeepSeek API (通过OpenAI兼容接口)
            response = await self.client.chat.completions.create(**api_params)
            
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
            
        except Exception as e:
            error_msg = str(e).lower()
            
            if "rate limit" in error_msg or "quota" in error_msg:
                raise RateLimitError(str(e), self.provider_type, "DEEPSEEK_RATE_LIMIT")
            elif "auth" in error_msg or "api key" in error_msg:
                raise AuthenticationError(str(e), self.provider_type, "DEEPSEEK_AUTH_ERROR")
            elif "model" in error_msg and "not found" in error_msg:
                raise ModelNotFoundError(str(e), self.provider_type, "DEEPSEEK_MODEL_NOT_FOUND")
            else:
                raise ProviderError(f"DeepSeek API错误: {str(e)}", self.provider_type, "DEEPSEEK_API_ERROR")
    
    async def _handle_streaming(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """
        处理DeepSeek流式响应
        
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
            self.logger.error(f"DeepSeek流式处理错误: {str(e)}")
            raise ProviderError(f"流式处理失败: {str(e)}", self.provider_type, "STREAMING_ERROR")
    
    def _build_api_params(self, request: LLMRequest) -> Dict[str, Any]:
        """
        构建DeepSeek API请求参数
        
        参数:
            request: LLM请求对象
            
        返回:
            Dict[str, Any]: API请求参数
        """
        # 获取模型配置
        model = request.model or self._get_default_model(request)
        model_config = self.config.models.get(model, {})
        
        # 格式化消息并添加系统提示
        messages = self._format_messages(request.messages, request)
        
        params = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature or model_config.get("temperature", 0.7),
            "max_tokens": request.max_tokens or model_config.get("max_tokens", 4096)
        }
        
        # 中文优化：降低温度提高准确性
        if self._is_chinese_content(request.messages):
            params["temperature"] = min(params["temperature"], 0.3)
        
        return params
    
    def _format_messages(self, messages: List[Dict[str, Any]], request: LLMRequest) -> List[Dict[str, Any]]:
        """
        格式化消息为DeepSeek格式，并添加优化的系统提示
        
        参数:
            messages: 原始消息列表
            request: LLM请求对象
            
        返回:
            List[Dict[str, Any]]: 格式化后的消息列表
        """
        formatted_messages = []
        has_system = False
        
        # 检查内容特征
        is_chinese = self._is_chinese_content(messages)
        is_code_related = self._is_code_related(messages)
        
        # 处理原始消息
        for msg in messages:
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "system":
                    has_system = True
                    formatted_messages.append({
                        "role": "system",
                        "content": content
                    })
                elif role in ["user", "assistant"]:
                    formatted_messages.append({
                        "role": role,
                        "content": content
                    })
        
        # 如果没有系统消息，根据内容特征添加优化提示
        if not has_system:
            system_content = ""
            
            if is_code_related:
                system_content = self.code_system_prompt
            elif is_chinese:
                system_content = self.chinese_system_prompt
            
            if system_content:
                formatted_messages.insert(0, {
                    "role": "system",
                    "content": system_content
                })
        
        return formatted_messages
    
    def _is_code_related(self, messages: List[Dict[str, Any]]) -> bool:
        """
        检测消息是否与编程相关
        
        参数:
            messages: 消息列表
            
        返回:
            bool: 是否与编程相关
        """
        code_keywords = {
            'python', 'javascript', 'java', 'cpp', 'c++', 'go', 'rust', 'php',
            'html', 'css', 'sql', 'bash', 'shell', '代码', '编程', '程序',
            'function', 'class', 'import', 'def', 'var', 'let', 'const',
            '函数', '类', '方法', '算法', '数据结构', 'api', '接口'
        }
        
        for msg in messages:
            if isinstance(msg, dict) and "content" in msg:
                content = str(msg["content"]).lower()
                if any(keyword in content for keyword in code_keywords):
                    return True
        
        return False
    
    def _get_default_model(self, request: LLMRequest) -> str:
        """
        根据请求类型获取默认DeepSeek模型
        
        参数:
            request: LLM请求对象
            
        返回:
            str: 默认模型名称
        """
        # 检查是否与编程相关
        if self._is_code_related(request.messages):
            return "deepseek-coder"  # 代码生成任务
        
        # 根据智能体类型选择模型
        agent_type = request.agent_type
        if agent_type in ["product", "sales"]:
            return "deepseek-v2"  # 商业知识和推理
        else:
            return "deepseek-chat"  # 通用对话任务
    
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
        # 从模型名称中提取基础模型类型
        base_model = "deepseek-chat"  # 默认
        if "coder" in model.lower():
            base_model = "deepseek-coder"
        elif "v2" in model.lower():
            base_model = "deepseek-v2"
        
        if base_model not in self.pricing:
            # 使用默认价格(非常便宜)
            return total_tokens * 0.0002 / 1000
        
        pricing = self.pricing[base_model]
        
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
        获取DeepSeek可用模型列表
        
        返回:
            List[ModelConfig]: 可用模型配置列表
        """
        models = [
            ModelConfig(
                model_name="deepseek-chat",
                display_name="DeepSeek Chat",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CHINESE_OPTIMIZATION,
                    ModelCapability.REASONING,
                    ModelCapability.COST_EFFECTIVE
                ],
                max_tokens=4096,
                cost_per_1k_tokens=0.00021,
                supports_chinese=True
            ),
            ModelConfig(
                model_name="deepseek-coder",
                display_name="DeepSeek Coder",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.CHINESE_OPTIMIZATION,
                    ModelCapability.COST_EFFECTIVE
                ],
                max_tokens=4096,
                cost_per_1k_tokens=0.00021,
                supports_chinese=True
            ),
            ModelConfig(
                model_name="deepseek-v2",
                display_name="DeepSeek V2",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.REASONING,
                    ModelCapability.CHINESE_OPTIMIZATION,
                    ModelCapability.COST_EFFECTIVE
                ],
                max_tokens=8192,
                cost_per_1k_tokens=0.00021,
                supports_chinese=True
            )
        ]
        
        return models
    
    async def test_connection(self) -> bool:
        """
        测试DeepSeek连接
        
        返回:
            bool: 连接是否成功
        """
        try:
            # 发送简单的测试请求
            response = await self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            return True
        except Exception as e:
            self.logger.error(f"DeepSeek连接测试失败: {str(e)}")
            return False