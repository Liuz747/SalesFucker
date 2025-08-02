"""
Google Gemini供应商实现模块

该模块实现了Google Gemini LLM供应商的具体功能，包括Gemini系列模型的调用、
多模态处理、流式响应和中文优化。Gemini在多模态理解和性价比方面表现优异。

核心功能:
- Gemini-1.5-Pro、Gemini-1.5-Flash 等模型支持
- 强大的多模态处理能力(文本、图像、视频)
- 流式和非流式响应处理
- 中文语言优化和文化理解
- 高性价比的API定价
"""

from typing import Dict, Any, Optional, List, AsyncGenerator
import google.generativeai as genai
import base64
import io
import time
from PIL import Image

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


class GeminiProvider(BaseProvider):
    """
    Google Gemini供应商实现类
    
    提供Gemini系列模型的完整支持，特别在多模态处理和中文理解方面
    表现优异。Gemini具有优秀的性价比和强大的推理能力。
    """
    
    def __init__(self, config: ProviderConfig):
        """
        初始化Gemini供应商
        
        参数:
            config: Gemini供应商配置
        """
        super().__init__(config)
        
        # 配置Gemini API
        genai.configure(api_key=config.credentials.api_key)
        
        # Gemini模型定价(每1K tokens)
        self.pricing = {
            "gemini-1.5-pro": {"input": 0.0035, "output": 0.0105},
            "gemini-1.5-flash": {"input": 0.00035, "output": 0.00105},
            "gemini-1.0-pro": {"input": 0.0005, "output": 0.0015}
        }
        
        # 中文优化指令
        self.chinese_instructions = """请用流畅自然的中文回答，注意：
1. 使用地道的中文表达方式
2. 理解中文语境和文化含义
3. 保持回答的准确性和专业性
4. 根据语境调整正式程度
5. 考虑中国本土化需求"""
        
        # 模型客户端缓存
        self.model_clients = {}
        
        self.logger.info("Google Gemini供应商初始化完成")
    
    async def _make_request(self, request: LLMRequest) -> LLMResponse:
        """
        执行Gemini API请求
        
        参数:
            request: LLM请求对象
            
        返回:
            LLMResponse: API响应对象
        """
        try:
            start_time = time.time()
            
            # 获取模型客户端
            model = self._get_model_client(request)
            
            # 构建请求内容
            content = self._build_content(request)
            
            # 设置生成配置
            generation_config = self._build_generation_config(request)
            
            # 调用Gemini API
            response = await model.generate_content_async(
                content,
                generation_config=generation_config
            )
            
            # 处理响应
            response_text = response.text if response.text else ""
            usage_tokens = self._estimate_tokens(request, response_text)
            model_name = request.model or self._get_default_model(request)
            
            # 计算成本
            cost = self._calculate_cost(model_name, usage_tokens)
            
            response_time = time.time() - start_time
            
            return LLMResponse(
                request_id=request.request_id,
                provider_type=self.provider_type,
                model=model_name,
                content=response_text,
                usage_tokens=usage_tokens,
                cost=cost,
                response_time=response_time,
                metadata={
                    "finish_reason": response.candidates[0].finish_reason.name if response.candidates else "STOP",
                    "safety_ratings": [
                        {
                            "category": rating.category.name,
                            "probability": rating.probability.name
                        }
                        for rating in (response.candidates[0].safety_ratings if response.candidates else [])
                    ]
                }
            )
            
        except Exception as e:
            error_msg = str(e).lower()
            
            if "quota" in error_msg or "rate" in error_msg:
                raise RateLimitError(str(e), self.provider_type, "GEMINI_RATE_LIMIT")
            elif "auth" in error_msg or "api key" in error_msg:
                raise AuthenticationError(str(e), self.provider_type, "GEMINI_AUTH_ERROR")
            elif "model" in error_msg and "not found" in error_msg:
                raise ModelNotFoundError(str(e), self.provider_type, "GEMINI_MODEL_NOT_FOUND")
            else:
                raise ProviderError(f"Gemini API错误: {str(e)}", self.provider_type, "GEMINI_API_ERROR")
    
    async def _handle_streaming(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """
        处理Gemini流式响应
        
        参数:
            request: LLM请求对象
            
        生成:
            str: 流式响应内容片段
        """
        try:
            # 获取模型客户端
            model = self._get_model_client(request)
            
            # 构建请求内容
            content = self._build_content(request)
            
            # 设置生成配置
            generation_config = self._build_generation_config(request)
            
            # 创建流式请求
            response = await model.generate_content_async(
                content,
                generation_config=generation_config,
                stream=True
            )
            
            # 逐个处理响应块
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            self.logger.error(f"Gemini流式处理错误: {str(e)}")
            raise ProviderError(f"流式处理失败: {str(e)}", self.provider_type, "STREAMING_ERROR")
    
    def _get_model_client(self, request: LLMRequest):
        """
        获取模型客户端(带缓存)
        
        参数:
            request: LLM请求对象
            
        返回:
            模型客户端对象
        """
        model_name = request.model or self._get_default_model(request)
        
        if model_name not in self.model_clients:
            # 检查是否包含中文内容
            is_chinese = self._is_chinese_content(request.messages)
            
            # 构建系统指令
            system_instruction = None
            if is_chinese:
                system_instruction = self.chinese_instructions
            
            # 创建模型客户端
            self.model_clients[model_name] = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_instruction
            )
        
        return self.model_clients[model_name]
    
    def _build_content(self, request: LLMRequest) -> List[Any]:
        """
        构建Gemini API内容
        
        参数:
            request: LLM请求对象
            
        返回:
            List[Any]: Gemini格式的内容列表
        """
        content_parts = []
        
        for msg in request.messages:
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                
                # 跳过系统消息(已在model创建时处理)
                if role == "system":
                    continue
                
                # 处理文本内容
                if "content" in msg:
                    content_parts.append(msg["content"])
                
                # 处理图像内容
                if "image_url" in msg:
                    image_data = self._process_image(msg["image_url"])
                    if image_data:
                        content_parts.append(image_data)
                        # 添加图像分析提示
                        if "text" in msg:
                            content_parts.append(msg["text"])
                        else:
                            content_parts.append("请分析这个图像并描述其内容。")
        
        return content_parts
    
    def _process_image(self, image_url: str) -> Optional[Any]:
        """
        处理图像数据为Gemini格式
        
        参数:
            image_url: 图像URL或base64数据
            
        返回:
            Gemini图像对象或None
        """
        try:
            if image_url.startswith("data:image"):
                # 处理base64图像
                header, data = image_url.split(",", 1)
                image_data = base64.b64decode(data)
                
                # 创建PIL图像对象
                image = Image.open(io.BytesIO(image_data))
                return image
            
            elif image_url.startswith("http"):
                # TODO: 实现HTTP图像下载
                self.logger.warning("HTTP图像URL暂不支持")
                return None
            
            else:
                # 尝试作为本地文件路径
                try:
                    image = Image.open(image_url)
                    return image
                except:
                    return None
                    
        except Exception as e:
            self.logger.error(f"图像处理失败: {str(e)}")
            return None
    
    def _build_generation_config(self, request: LLMRequest) -> Dict[str, Any]:
        """
        构建Gemini生成配置
        
        参数:
            request: LLM请求对象
            
        返回:
            Dict[str, Any]: 生成配置
        """
        model = request.model or self._get_default_model(request)
        model_config = self.config.models.get(model, {})
        
        config = {
            "temperature": request.temperature or model_config.get("temperature", 0.7),
            "max_output_tokens": request.max_tokens or model_config.get("max_tokens", 8192),
            "top_p": 0.8,
            "top_k": 40
        }
        
        # 中文优化：降低温度提高准确性
        if self._is_chinese_content(request.messages):
            config["temperature"] = min(config["temperature"], 0.3)
        
        return genai.GenerationConfig(**config)
    
    def _get_default_model(self, request: LLMRequest) -> str:
        """
        根据请求类型获取默认Gemini模型
        
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
            return "gemini-1.5-pro"  # Pro版本对图像处理更好
        
        # 根据智能体类型选择模型
        agent_type = request.agent_type
        if agent_type in ["compliance", "sentiment", "intent"]:
            return "gemini-1.5-pro"  # 高质量分析任务
        elif agent_type in ["sales", "product"]:
            return "gemini-1.5-pro"  # 复杂推理任务
        else:
            return "gemini-1.5-flash"  # 快速响应任务
    
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
    
    def _estimate_tokens(self, request: LLMRequest, response_text: str) -> int:
        """
        估算令牌使用量(Gemini API不提供精确计数)
        
        参数:
            request: 请求对象
            response_text: 响应文本
            
        返回:
            int: 估算的令牌数量
        """
        # 简单估算：中文约1.5字符/token，英文约4字符/token
        input_text = " ".join([
            msg.get("content", "") for msg in request.messages 
            if isinstance(msg, dict) and "content" in msg
        ])
        
        # 检查是否主要是中文
        is_chinese = self._is_chinese_content(request.messages)
        
        if is_chinese:
            input_tokens = len(input_text) / 1.5
            output_tokens = len(response_text) / 1.5
        else:
            input_tokens = len(input_text) / 4
            output_tokens = len(response_text) / 4
        
        return int(input_tokens + output_tokens)
    
    def _calculate_cost(self, model: str, total_tokens: int) -> float:
        """
        计算请求成本
        
        参数:
            model: 使用的模型
            total_tokens: 总令牌数
            
        返回:
            float: 请求成本(美元)
        """
        if model not in self.pricing:
            # 使用默认价格
            return total_tokens * 0.001 / 1000
        
        pricing = self.pricing[model]
        
        # 由于Gemini不提供精确的输入输出分离，使用平均价格
        avg_price = (pricing["input"] + pricing["output"]) / 2
        return (total_tokens / 1000) * avg_price
    
    async def get_available_models(self) -> List[ModelConfig]:
        """
        获取Gemini可用模型列表
        
        返回:
            List[ModelConfig]: 可用模型配置列表
        """
        models = [
            ModelConfig(
                model_name="gemini-1.5-pro",
                display_name="Gemini 1.5 Pro",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.MULTIMODAL,
                    ModelCapability.REASONING,
                    ModelCapability.CHINESE_OPTIMIZATION
                ],
                max_tokens=8192,
                cost_per_1k_tokens=0.007,
                supports_chinese=True
            ),
            ModelConfig(
                model_name="gemini-1.5-flash",
                display_name="Gemini 1.5 Flash",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.MULTIMODAL,
                    ModelCapability.FAST_RESPONSE,
                    ModelCapability.COST_EFFECTIVE,
                    ModelCapability.CHINESE_OPTIMIZATION
                ],
                max_tokens=8192,
                cost_per_1k_tokens=0.0007,
                supports_chinese=True
            ),
            ModelConfig(
                model_name="gemini-1.0-pro",
                display_name="Gemini 1.0 Pro",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.REASONING,
                    ModelCapability.CHINESE_OPTIMIZATION,
                    ModelCapability.COST_EFFECTIVE
                ],
                max_tokens=4096,
                cost_per_1k_tokens=0.001,
                supports_chinese=True
            )
        ]
        
        return models
    
    async def test_connection(self) -> bool:
        """
        测试Gemini连接
        
        返回:
            bool: 连接是否成功
        """
        try:
            # 创建测试模型
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            # 发送简单的测试请求
            response = await model.generate_content_async("Hello")
            
            return response.text is not None
        except Exception as e:
            self.logger.error(f"Gemini连接测试失败: {str(e)}")
            return False