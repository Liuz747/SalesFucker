"""
多LLM请求构建器模块

该模块负责构建和验证LLM请求对象，处理参数默认值和验证。
提供统一的请求构建接口，支持不同类型的LLM请求。

核心功能:
- LLM请求对象构建
- 参数验证和默认值处理
- 上下文信息提取
- 多模态内容检测
"""

import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..base_provider import LLMRequest, RequestType
from ..intelligent_router import RoutingContext
from src.utils import get_component_logger


class RequestBuilder:
    """
    LLM请求构建器
    
    负责构建标准化的LLM请求对象，处理参数验证和默认值设置。
    """
    
    def __init__(self):
        """初始化请求构建器"""
        self.logger = get_component_logger(__name__, "RequestBuilder")
    
    def build_chat_request(
        self,
        messages: List[Dict[str, Any]],
        agent_type: Optional[str] = None,
        tenant_id: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> LLMRequest:
        """
        构建聊天完成请求
        
        参数:
            messages: 消息列表
            agent_type: 智能体类型
            tenant_id: 租户ID
            model: 指定模型
            temperature: 温度参数
            max_tokens: 最大令牌数
            stream: 是否流式响应
            **kwargs: 其他参数
            
        返回:
            LLMRequest: 构建的请求对象
        """
        # 生成请求ID
        request_id = str(uuid.uuid4())
        
        # 验证消息格式
        validated_messages = self._validate_messages(messages)
        
        # 应用默认值
        effective_temperature = self._get_default_temperature(temperature, agent_type)
        effective_max_tokens = self._get_default_max_tokens(max_tokens, agent_type)
        
        # 创建请求对象
        request = LLMRequest(
            request_id=request_id,
            request_type=RequestType.CHAT_COMPLETION,
            messages=validated_messages,
            model=model,
            temperature=effective_temperature,
            max_tokens=effective_max_tokens,
            stream=stream,
            tenant_id=tenant_id,
            agent_type=agent_type,
            metadata=kwargs
        )
        
        self.logger.debug(f"构建聊天请求: {request_id}, 智能体: {agent_type}")
        return request
    
    def build_routing_context(
        self,
        agent_type: Optional[str],
        tenant_id: Optional[str],
        messages: List[Dict[str, Any]],
        **kwargs
    ) -> RoutingContext:
        """
        构建路由上下文
        
        参数:
            agent_type: 智能体类型
            tenant_id: 租户ID
            messages: 消息列表
            **kwargs: 其他参数
            
        返回:
            RoutingContext: 路由上下文对象
        """
        # 检测内容语言
        content_language = self._detect_content_language(messages)
        
        # 检测多模态内容
        has_multimodal = self._detect_multimodal_content(messages)
        
        # 获取配置参数
        urgency_level = kwargs.get("urgency", "medium")
        cost_priority = kwargs.get("cost_priority", 0.5)
        quality_threshold = kwargs.get("quality_threshold", 0.8)
        
        return RoutingContext(
            agent_type=agent_type,
            tenant_id=tenant_id,
            content_language=content_language,
            has_multimodal=has_multimodal,
            urgency_level=urgency_level,
            cost_priority=cost_priority,
            quality_threshold=quality_threshold
        )
    
    def _validate_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """验证消息格式"""
        if not messages:
            raise ValueError("消息列表不能为空")
        
        validated = []
        for i, message in enumerate(messages):
            if not isinstance(message, dict):
                raise ValueError(f"消息 {i} 必须是字典格式")
            
            if "role" not in message:
                raise ValueError(f"消息 {i} 缺少 'role' 字段")
            
            if "content" not in message:
                raise ValueError(f"消息 {i} 缺少 'content' 字段")
            
            validated.append(message)
        
        return validated
    
    def _get_default_temperature(
        self, 
        temperature: Optional[float], 
        agent_type: Optional[str]
    ) -> float:
        """获取默认温度值"""
        if temperature is not None:
            return max(0.0, min(2.0, temperature))  # 限制在合理范围内
        
        # 智能体类型特定默认值
        agent_defaults = {
            "compliance": 0.3,
            "sentiment": 0.4,
            "intent": 0.3,
            "sales": 0.7,
            "product": 0.5,
            "memory": 0.2,
            "suggestion": 0.4
        }
        
        return agent_defaults.get(agent_type, 0.7)
    
    def _get_default_max_tokens(
        self, 
        max_tokens: Optional[int], 
        agent_type: Optional[str]
    ) -> int:
        """获取默认最大令牌数"""
        if max_tokens is not None:
            return max(1, min(32000, max_tokens))  # 限制在合理范围内
        
        # 智能体类型特定默认值
        agent_defaults = {
            "compliance": 2048,
            "sentiment": 1024,
            "intent": 512,
            "sales": 4096,
            "product": 3072,
            "memory": 1024,
            "suggestion": 2048
        }
        
        return agent_defaults.get(agent_type, 2048)
    
    def _detect_content_language(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        """检测内容语言"""
        chinese_chars = set('的一是在不了有和人这中大为上个国我以要他时来用们生到作地于出就分对成会可主发年动同工也能下过子说产种面而方后多定行学法所民得经十三之进着等部度家电力里如水化高自二理起小物现实加量都两体制机当使点从业本去把性好应开它合还因由其些然前外天政四日那社义事平形相全表间样与关各重新线内数正心反你明看原又么利比或但质气第向道命此变条只没结解问意建月公无系军很情者最立代想已通并提直题党程展五果料象员革位入常文总次品式活设及管特件长求老头基资边流路级少图山统接知较将组见计别她手角期根论运农指几九区强放决西被干做必战先回则任取据处队南给色光门即保治北造百规热领七海口东导器压志世金增争济阶油思术极交受联什认六共权收证改清己美再采转更单风切打白教速花带安场身车例真务具万每目至达走积示议声报斗完类八离华名确才科张信马节话米整空元况今集温传土许步群广石记需段研界拉林律叫且究观越织装影算低持音众书布复容儿须际商非验连断深难近矿千周委素技备半办青省列习响约支般史感劳便团往酸历市克何除消构府称太准精值号率族维划选标写存候毛亲快效斯院查江型眼王按格养易置派层片始却专状育厂京识适属圆包火住调满县局照参红细引听该铁价严')
        
        for msg in messages:
            if isinstance(msg, dict) and "content" in msg:
                content = str(msg["content"])
                if any(char in chinese_chars for char in content):
                    return "zh"
        
        return "en"
    
    def _detect_multimodal_content(self, messages: List[Dict[str, Any]]) -> bool:
        """检测多模态内容"""
        for msg in messages:
            if isinstance(msg, dict):
                # 检查图像URL
                if "image_url" in msg:
                    return True
                # 检查内容数组（GPT-4V格式）
                if isinstance(msg.get("content"), list):
                    for content_item in msg["content"]:
                        if isinstance(content_item, dict) and content_item.get("type") == "image_url":
                            return True
        
        return False