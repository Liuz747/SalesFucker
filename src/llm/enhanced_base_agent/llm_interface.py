"""
LLM接口管理器模块

该模块提供智能体与多LLM客户端的统一接口。
处理LLM请求、响应和错误管理。

核心功能:
- LLM请求执行
- 响应处理和验证
- 错误处理和降级
- 统计信息收集
"""

import time
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

from ..multi_llm_client import MultiLLMClient, get_multi_llm_client
from ..intelligent_router import RoutingStrategy
from ..provider_config import GlobalProviderConfig
from src.utils import get_component_logger, ErrorHandler


class LLMInterface:
    """
    LLM接口管理器
    
    提供智能体与多LLM系统的统一接口。
    """
    
    def __init__(
        self, 
        agent_id: str,
        tenant_id: Optional[str] = None,
        llm_config: Optional[GlobalProviderConfig] = None
    ):
        """
        初始化LLM接口
        
        参数:
            agent_id: 智能体ID
            tenant_id: 租户ID
            llm_config: LLM配置
        """
        self.agent_id = agent_id
        self.tenant_id = tenant_id
        self.llm_config = llm_config
        self.logger = get_component_logger(__name__, "LLMInterface")
        self.error_handler = ErrorHandler("llm_interface")
        
        # LLM客户端引用
        self._llm_client: Optional[MultiLLMClient] = None
        
        # 统计信息
        self.llm_stats = {
            "total_llm_requests": 0,
            "successful_llm_requests": 0,
            "failed_llm_requests": 0,
            "total_llm_cost": 0.0,
            "avg_llm_response_time": 0.0,
            "provider_usage": {}
        }
    
    async def get_llm_client(self) -> MultiLLMClient:
        """获取多LLM客户端实例"""
        if self._llm_client is None:
            self._llm_client = await get_multi_llm_client(self.llm_config)
        return self._llm_client
    
    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        agent_type: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        strategy: Optional[RoutingStrategy] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        """
        执行LLM聊天完成请求
        
        参数:
            messages: 消息列表
            agent_type: 智能体类型
            model: 指定模型
            temperature: 温度参数
            max_tokens: 最大令牌数
            stream: 是否流式响应
            strategy: 路由策略
            **kwargs: 其他参数
            
        返回:
            Union[str, Dict[str, Any]]: 响应内容
        """
        start_time = time.time()
        
        try:
            # 获取LLM客户端
            llm_client = await self.get_llm_client()
            
            # 执行请求
            response = await llm_client.chat_completion(
                messages=messages,
                agent_type=agent_type,
                tenant_id=self.tenant_id,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                strategy=strategy,
                **kwargs
            )
            
            # 更新统计信息
            processing_time = time.time() - start_time
            self._update_llm_stats(processing_time, True)
            
            return response
            
        except Exception as e:
            processing_time = time.time() - start_time
            self._update_llm_stats(processing_time, False)
            
            # 使用错误处理器
            error_context = {
                "agent_id": self.agent_id,
                "agent_type": agent_type,
                "tenant_id": self.tenant_id,
                "processing_time": processing_time
            }
            self.error_handler.handle_error(e, error_context)
            raise
    
    async def analyze_sentiment(
        self,
        text: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        LLM情感分析
        
        参数:
            text: 要分析的文本
            **kwargs: 其他参数
            
        返回:
            Dict[str, Any]: 情感分析结果
        """
        try:
            llm_client = await self.get_llm_client()
            return await llm_client.analyze_sentiment(
                text=text,
                tenant_id=self.tenant_id,
                **kwargs
            )
        except Exception as e:
            self.logger.error(f"LLM情感分析失败: {str(e)}")
            # 返回默认结果
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.5,
                "error": str(e)
            }
    
    async def classify_intent(
        self,
        text: str,
        conversation_history: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        LLM意图分类
        
        参数:
            text: 要分类的文本
            conversation_history: 对话历史
            **kwargs: 其他参数
            
        返回:
            Dict[str, Any]: 意图分类结果
        """
        try:
            llm_client = await self.get_llm_client()
            return await llm_client.classify_intent(
                text=text,
                conversation_history=conversation_history,
                tenant_id=self.tenant_id,
                **kwargs
            )
        except Exception as e:
            self.logger.error(f"LLM意图分类失败: {str(e)}")
            # 返回默认结果
            return {
                "intent": "browsing",
                "category": "general",
                "confidence": 0.5,
                "urgency": "medium",
                "error": str(e)
            }
    
    async def generate_response(
        self,
        prompt: str,
        agent_type: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        生成LLM响应
        
        参数:
            prompt: 提示文本
            agent_type: 智能体类型
            context: 上下文信息
            **kwargs: 其他参数
            
        返回:
            str: 生成的响应
        """
        # 构建消息列表
        messages = [
            {
                "role": "system",
                "content": self._build_system_message(agent_type, context)
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        return await self.chat_completion(
            messages=messages,
            agent_type=agent_type,
            **kwargs
        )
    
    def _build_system_message(self, agent_type: str, context: Optional[Dict[str, Any]] = None) -> str:
        """构建系统消息"""
        base_message = f"你是一个专业的{agent_type}智能体，负责处理美妆相关的客户咨询。"
        
        # 添加上下文信息
        if context:
            if context.get("customer_profile"):
                base_message += f"\\n客户信息: {context['customer_profile']}"
            
            if context.get("conversation_history"):
                base_message += f"\\n对话历史: {context['conversation_history']}"
            
            if context.get("product_context"):
                base_message += f"\\n产品信息: {context['product_context']}"
        
        base_message += "\\n\\n请用中文回复，保持专业和友好的语调。"
        
        return base_message
    
    def _update_llm_stats(self, processing_time: float, success: bool):
        """更新LLM统计信息"""
        self.llm_stats["total_llm_requests"] += 1
        
        if success:
            self.llm_stats["successful_llm_requests"] += 1
            
            # 更新平均响应时间
            total_successful = self.llm_stats["successful_llm_requests"]
            current_avg = self.llm_stats["avg_llm_response_time"]
            self.llm_stats["avg_llm_response_time"] = (
                (current_avg * (total_successful - 1) + processing_time) / total_successful
            )
        else:
            self.llm_stats["failed_llm_requests"] += 1
    
    async def get_llm_stats(self) -> Dict[str, Any]:
        """获取LLM统计信息"""
        try:
            llm_client = await self.get_llm_client()
            global_stats = await llm_client.get_global_stats()
            
            return {
                "agent_stats": self.llm_stats.copy(),
                "global_stats": global_stats,
                "agent_id": self.agent_id,
                "tenant_id": self.tenant_id
            }
        except Exception as e:
            self.logger.error(f"获取LLM统计信息失败: {str(e)}")
            return {"error": str(e)}
    
    async def get_cost_analysis(self) -> Dict[str, Any]:
        """获取成本分析"""
        try:
            llm_client = await self.get_llm_client()
            return await llm_client.get_cost_analysis(tenant_id=self.tenant_id)
        except Exception as e:
            self.logger.error(f"获取成本分析失败: {str(e)}")
            return {"error": str(e)}
    
    async def get_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """获取优化建议"""
        try:
            llm_client = await self.get_llm_client()
            return await llm_client.get_optimization_suggestions(tenant_id=self.tenant_id)
        except Exception as e:
            self.logger.error(f"获取优化建议失败: {str(e)}")
            return []
    
    def reset_stats(self):
        """重置统计信息"""
        self.llm_stats = {
            "total_llm_requests": 0,
            "successful_llm_requests": 0,
            "failed_llm_requests": 0,
            "total_llm_cost": 0.0,
            "avg_llm_response_time": 0.0,
            "provider_usage": {}
        }
        self.logger.info(f"LLM统计信息已重置: {self.agent_id}")
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """获取健康指标"""
        total_requests = self.llm_stats["total_llm_requests"]
        error_rate = 0.0
        
        if total_requests > 0:
            error_rate = (self.llm_stats["failed_llm_requests"] / total_requests) * 100
        
        # 评估健康状态
        health_status = "healthy"
        if error_rate > 20:  # 超过20%错误率
            health_status = "critical"
        elif error_rate > 10:  # 超过10%错误率
            health_status = "warning"
        
        return {
            "health_status": health_status,
            "error_rate": error_rate,
            "avg_response_time": self.llm_stats["avg_llm_response_time"],
            "total_requests": total_requests,
            "successful_requests": self.llm_stats["successful_llm_requests"],
            "failed_requests": self.llm_stats["failed_llm_requests"]
        }