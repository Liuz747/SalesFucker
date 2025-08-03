"""
多LLM API处理器模块

该模块提供多LLM系统的API处理逻辑，包括供应商管理、成本追踪和配置管理。
专门为API端点提供多LLM功能支持，保持API文件的简洁性。
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

from src.llm.multi_llm_client import get_multi_llm_client
from src.llm.provider_config import GlobalProviderConfig, ProviderType
from src.utils import get_component_logger, ErrorHandler


class MultiLLMAPIHandler:
    """
    多LLM API处理器
    
    提供API端点所需的多LLM功能，包括配置管理、状态监控和成本追踪。
    """
    
    def __init__(self):
        self.logger = get_component_logger(__name__, "MultiLLMAPIHandler")
        self.error_handler = ErrorHandler("multi_llm_api")
        self._client = None
    
    async def get_client(self):
        """获取多LLM客户端实例"""
        if self._client is None:
            config = await self._load_default_config()
            self._client = await get_multi_llm_client(config)
        return self._client
    
    async def _load_default_config(self) -> GlobalProviderConfig:
        """加载默认配置"""
        # 这里应该从配置文件或环境变量加载
        # 暂时使用硬编码的基础配置
        import os
        
        config = GlobalProviderConfig()
        
        # 添加OpenAI配置（如果API key存在）
        if os.getenv("OPENAI_API_KEY"):
            from src.llm.provider_config import ProviderConfig, ProviderCredentials, ModelConfig
            
            openai_creds = ProviderCredentials(
                provider_type=ProviderType.OPENAI,
                api_key=os.getenv("OPENAI_API_KEY"),
                organization=os.getenv("OPENAI_ORGANIZATION")
            )
            
            openai_models = {
                "gpt-4": ModelConfig(
                    model_name="gpt-4",
                    display_name="GPT-4",
                    max_tokens=8192,
                    cost_per_1k_tokens=0.03
                ),
                "gpt-3.5-turbo": ModelConfig(
                    model_name="gpt-3.5-turbo",
                    display_name="GPT-3.5 Turbo",
                    max_tokens=4096,
                    cost_per_1k_tokens=0.002
                )
            }
            
            openai_config = ProviderConfig(
                provider_type=ProviderType.OPENAI,
                credentials=openai_creds,
                models=openai_models,
                priority=1
            )
            
            config.default_providers["openai"] = openai_config
        
        return config
    
    async def enhance_conversation_with_llm_routing(
        self,
        request_data: Dict[str, Any],
        orchestrator_result: Any
    ) -> Dict[str, Any]:
        """
        使用多LLM路由增强对话处理结果
        
        参数:
            request_data: 请求数据
            orchestrator_result: 原始编排器结果
            
        返回:
            增强后的结果数据
        """
        try:
            client = await self.get_client()
            
            # 获取使用的供应商和模型信息
            provider_status = await client.get_provider_status(
                tenant_id=request_data.get("tenant_id")
            )
            
            # 增强响应数据
            enhanced_data = {
                "llm_provider_used": self._extract_used_provider(provider_status),
                "model_used": self._extract_used_model(provider_status),
                "processing_cost": await self._calculate_processing_cost(client, request_data),
                "token_usage": await self._get_token_usage(client, request_data),
                "provider_health": self._get_provider_health_summary(provider_status)
            }
            
            return enhanced_data
            
        except Exception as e:
            self.logger.error(f"多LLM路由增强失败: {e}")
            # 返回默认值，不影响主要功能
            return {
                "llm_provider_used": "openai",  # 默认值
                "model_used": "gpt-3.5-turbo",
                "processing_cost": 0.0,
                "token_usage": {"total": 0},
                "provider_health": "unknown"
            }
    
    def _extract_used_provider(self, provider_status: Dict[str, Any]) -> str:
        """提取实际使用的供应商"""
        for provider, status in provider_status.items():
            if status.get("is_healthy", False):
                return provider
        return "openai"  # 默认
    
    def _extract_used_model(self, provider_status: Dict[str, Any]) -> str:
        """提取实际使用的模型"""
        # 这里应该从实际的LLM调用中获取
        return "gpt-3.5-turbo"  # 默认
    
    async def _calculate_processing_cost(
        self,
        client,
        request_data: Dict[str, Any]
    ) -> float:
        """计算处理成本"""
        try:
            # 获取最近的成本分析
            cost_analysis = await client.get_cost_analysis(
                tenant_id=request_data.get("tenant_id"),
                start_time=datetime.now() - timedelta(hours=1),
                end_time=datetime.now()
            )
            
            return cost_analysis.get("avg_cost_per_request", 0.0)
            
        except Exception:
            return 0.0
    
    async def _get_token_usage(
        self,
        client,
        request_data: Dict[str, Any]
    ) -> Dict[str, int]:
        """获取令牌使用统计"""
        try:
            stats = await client.get_global_stats()
            client_stats = stats.get("client_stats", {})
            
            return {
                "total": client_stats.get("total_tokens", 0),
                "input": client_stats.get("input_tokens", 0),
                "output": client_stats.get("output_tokens", 0)
            }
            
        except Exception:
            return {"total": 0, "input": 0, "output": 0}
    
    def _get_provider_health_summary(self, provider_status: Dict[str, Any]) -> str:
        """获取供应商健康状态摘要"""
        healthy_count = sum(1 for status in provider_status.values() 
                           if status.get("is_healthy", False))
        total_count = len(provider_status)
        
        if healthy_count == total_count and total_count > 0:
            return "excellent"
        elif healthy_count >= total_count * 0.8:
            return "good"
        elif healthy_count >= total_count * 0.5:
            return "fair"
        else:
            return "poor"


