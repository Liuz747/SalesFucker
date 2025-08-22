"""
LLM管理业务逻辑处理器

该模块实现LLM提供商管理相关的业务逻辑，包括提供商配置、状态监控、
成本分析、路由优化等功能。

主要功能:
- LLM提供商配置和管理
- 提供商健康状态监控
- 成本分析和预算控制
- 智能路由策略配置
- 性能优化和对比分析
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from utils import get_component_logger
from ..schemas.llm import (
    LLMConfigRequest,
    ProviderStatusRequest,
    LLMStatusResponse,
    CostAnalysisResponse,
    LLMProviderType,
    ProviderInfo,
)
from ..exceptions import (
    LLMProviderException,
    ValidationException
)

logger = get_component_logger(__name__, "LLMHandler")


class LLMHandler:
    """LLM管理业务逻辑处理器"""
    
    def __init__(self):
        """初始化处理器"""
        self.logger = logger
    
    async def get_provider_status(
        self,
        tenant_id: str,
        status_request: ProviderStatusRequest,
        llm_service
    ) -> LLMStatusResponse:
        """
        获取提供商状态信息
        
        Args:
            tenant_id: 租户ID
            status_request: 状态请求
            llm_service: LLM服务实例
            
        Returns:
            LLM状态响应
        """
        try:
            # 获取提供商信息
            providers_info = []
            
            if status_request.provider:
                # 获取特定提供商状态
                provider_info = await self._get_single_provider_status(
                    status_request.provider, tenant_id, llm_service
                )
                if provider_info:
                    providers_info.append(provider_info)
            else:
                # 获取所有提供商状态
                all_providers = [
                    LLMProviderType.OPENAI,
                    LLMProviderType.ANTHROPIC,
                    LLMProviderType.GEMINI,
                    LLMProviderType.DEEPSEEK
                ]
                
                for provider in all_providers:
                    provider_info = await self._get_single_provider_status(
                        provider, tenant_id, llm_service
                    )
                    if provider_info:
                        providers_info.append(provider_info)
            
            # 获取路由配置
            routing_config = await self._get_routing_config(tenant_id, llm_service)
            
            # 系统级指标
            system_metrics = None
            if status_request.include_metrics:
                system_metrics = await self._get_system_metrics(
                    tenant_id, status_request.time_range_hours, llm_service
                )
            
            return LLMStatusResponse(
                success=True,
                message="LLM状态获取成功",
                data={
                    "tenant_id": tenant_id,
                    "timestamp": datetime.now().isoformat()
                },
                providers=providers_info,
                routing_config=routing_config,
                system_metrics=system_metrics
            )
            
        except Exception as e:
            self.logger.error(f"获取提供商状态失败: {e}", exc_info=True)
            raise ValidationException(f"获取提供商状态失败: {str(e)}")
    
    async def _get_single_provider_status(
        self,
        provider: LLMProviderType,
        tenant_id: str,
        llm_service
    ) -> Optional[ProviderInfo]:
        """获取单个提供商状态"""
        try:
            # 这里应该调用实际的LLM服务来获取状态
            # 目前返回模拟数据
            return ProviderInfo(
                provider=provider,
                model_name=self._get_default_model(provider),
                status="active",
                enabled=True,
                priority=1,
                endpoint_url=self._get_provider_endpoint(provider),
                last_health_check=datetime.now(),
                rate_limits={"requests_per_minute": 60, "tokens_per_minute": 100000},
                model_config={"temperature": 0.7, "max_tokens": 4000}
            )
        except Exception as e:
            self.logger.warning(f"获取提供商状态失败 {provider}: {e}")
            return None
    
    def _get_default_model(self, provider: LLMProviderType) -> str:
        """获取提供商默认模型"""
        model_mapping = {
            LLMProviderType.OPENAI: "gpt-4",
            LLMProviderType.ANTHROPIC: "claude-3-sonnet-20240229",
            LLMProviderType.GEMINI: "gemini-pro",
            LLMProviderType.DEEPSEEK: "deepseek-chat"
        }
        return model_mapping.get(provider, "unknown")
    
    def _get_provider_endpoint(self, provider: LLMProviderType) -> str:
        """获取提供商API端点"""
        endpoint_mapping = {
            LLMProviderType.OPENAI: "https://api.openai.com/v1",
            LLMProviderType.ANTHROPIC: "https://api.anthropic.com/v1",
            LLMProviderType.GEMINI: "https://generativelanguage.googleapis.com/v1",
            LLMProviderType.DEEPSEEK: "https://api.deepseek.com/v1"
        }
        return endpoint_mapping.get(provider, "")
    
    async def _get_routing_config(self, tenant_id: str, llm_service) -> Dict[str, Any]:
        """获取路由配置"""
        return {
            "strategy": "AGENT_OPTIMIZED",
            "fallback_provider": LLMProviderType.OPENAI.value,
            "health_check_interval": 60,
            "last_updated": datetime.now().isoformat()
        }
    
    async def _get_system_metrics(
        self, tenant_id: str, time_range_hours: int, llm_service
    ) -> Dict[str, Any]:
        """获取系统级指标"""
        return {
            "total_requests": 1500,
            "successful_requests": 1485,
            "failed_requests": 15,
            "average_response_time": 850.5,
            "total_cost": 45.67,
            "time_range": {
                "start": (datetime.now() - timedelta(hours=time_range_hours)).isoformat(),
                "end": datetime.now().isoformat()
            }
        }
    
    async def configure_provider(
        self,
        tenant_id: str,
        config_request: LLMConfigRequest,
        llm_service
    ) -> Dict[str, Any]:
        """配置LLM提供商"""
        try:
            # 验证配置
            await self._validate_provider_config(config_request)
            
            # 应用配置（这里应该调用实际的LLM服务）
            config_result = {
                "provider": config_request.provider.value,
                "model_name": config_request.model_name,
                "configured_at": datetime.now().isoformat(),
                "status": "configured"
            }
            
            self.logger.info(f"提供商配置成功: {config_request.provider} for tenant {tenant_id}")
            
            return {
                "success": True,
                "message": f"提供商 {config_request.provider.value} 配置成功",
                "config": config_result
            }
            
        except Exception as e:
            self.logger.error(f"配置提供商失败: {e}", exc_info=True)
            raise ValidationException(f"配置提供商失败: {str(e)}")
    
    async def _validate_provider_config(self, config: LLMConfigRequest):
        """验证提供商配置"""
        required_fields = {
            LLMProviderType.OPENAI: ["api_key"],
            LLMProviderType.ANTHROPIC: ["api_key"],
            LLMProviderType.GEMINI: ["api_key"],
            LLMProviderType.DEEPSEEK: ["api_key"]
        }
        
        provider_required = required_fields.get(config.provider, [])
        
        for field in provider_required:
            if field == "api_key" and not config.api_key:
                raise ValidationException(f"提供商 {config.provider.value} 需要 API 密钥")
    
    async def get_cost_analysis(
        self,
        tenant_id: str,
        days: int,
        provider: Optional[LLMProviderType],
        llm_service
    ) -> CostAnalysisResponse:
        """获取成本分析"""
        try:
            # 模拟成本数据
            cost_data = self._generate_mock_cost_data(days, provider)
            
            return CostAnalysisResponse(
                success=True,
                message="成本分析获取成功",
                data=cost_data,
                total_cost=cost_data["total_cost"],
                cost_breakdown=cost_data["cost_breakdown"],
                monthly_budget=cost_data.get("monthly_budget"),
                budget_utilization=cost_data.get("budget_utilization"),
                daily_costs=cost_data["daily_costs"],
                cost_trends=cost_data["cost_trends"],
                optimization_suggestions=cost_data["optimization_suggestions"]
            )
            
        except Exception as e:
            self.logger.error(f"获取成本分析失败: {e}", exc_info=True)
            raise ValidationException(f"获取成本分析失败: {str(e)}")
    
    def _generate_mock_cost_data(self, days: int, provider: Optional[LLMProviderType]) -> Dict[str, Any]:
        """生成模拟成本数据"""
        import random
        
        if provider:
            providers = [provider]
        else:
            providers = list(LLMProviderType)
        
        cost_breakdown = {}
        daily_costs = []
        cost_trends = {}
        
        for provider in providers:
            daily_cost = random.uniform(5, 50)
            total_provider_cost = daily_cost * days
            cost_breakdown[provider] = round(total_provider_cost, 2)
            
            # 生成趋势数据
            trend = [daily_cost * random.uniform(0.8, 1.2) for _ in range(days)]
            cost_trends[provider.value] = trend
        
        # 生成每日成本
        for day in range(days):
            day_total = sum(cost_trends[p.value][day] for p in providers)
            daily_costs.append({
                "date": (datetime.now() - timedelta(days=days-day-1)).strftime("%Y-%m-%d"),
                "total_cost": round(day_total, 2),
                "breakdown": {p.value: round(cost_trends[p.value][day], 2) for p in providers}
            })
        
        total_cost = sum(cost_breakdown.values())
        
        return {
            "total_cost": round(total_cost, 2),
            "cost_breakdown": cost_breakdown,
            "monthly_budget": 1000.0,
            "budget_utilization": round((total_cost / 1000.0) * 100, 1),
            "daily_costs": daily_costs,
            "cost_trends": cost_trends,
            "optimization_suggestions": [
                {
                    "type": "provider_switch",
                    "message": "考虑在非关键任务中使用成本更低的DeepSeek模型",
                    "potential_savings": round(total_cost * 0.25, 2)
                },
                {
                    "type": "rate_limiting",
                    "message": "设置合理的速率限制可以避免意外的高成本",
                    "potential_savings": round(total_cost * 0.10, 2)
                }
            ]
        }
    
    async def test_provider(self, provider: LLMProviderType, test_message: str, model_name: Optional[str], tenant_id: str, llm_service) -> Dict[str, Any]:
        """测试提供商"""
        return {
            "success": True,
            "provider": provider.value,
            "model": model_name or self._get_default_model(provider),
            "response_time_ms": 850.5,
            "test_response": "This is a test response from the provider."
        }
    
    async def toggle_provider(self, provider: LLMProviderType, enabled: bool, tenant_id: str, llm_service) -> Dict[str, Any]:
        """启用/禁用提供商"""
        action = "启用" if enabled else "禁用"
        return {"success": True, "message": f"提供商 {provider.value} 已{action}"}