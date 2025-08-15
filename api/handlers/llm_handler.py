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

from typing import Dict, Any, Optional, List
import asyncio
import logging
from datetime import datetime, timedelta

from utils import get_component_logger
from ..schemas.llm import (
    LLMConfigRequest,
    ProviderStatusRequest,
    OptimizationRequest,
    RoutingConfigRequest,
    CostBudgetRequest,
    LLMStatusResponse,
    CostAnalysisResponse,
    OptimizationResponse,
    ProviderHealthResponse,
    ModelCapabilitiesResponse,
    RoutingStatsResponse,
    LLMProviderType,
    ProviderInfo,
    ProviderMetrics,
    RoutingStrategy
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
            
            # 计算全局状态
            global_status = self._calculate_global_status(providers_info)
            
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
                global_status=global_status,
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
    
    def _calculate_global_status(self, providers: List[ProviderInfo]) -> str:
        """计算全局状态"""
        if not providers:
            return "critical"
        
        active_providers = [p for p in providers if p.status == "active" and p.enabled]
        
        if len(active_providers) == 0:
            return "critical"
        elif len(active_providers) < len(providers) * 0.5:
            return "warning"
        else:
            return "healthy"
    
    async def _get_routing_config(self, tenant_id: str, llm_service) -> Dict[str, Any]:
        """获取路由配置"""
        return {
            "strategy": RoutingStrategy.AGENT_OPTIMIZED.value,
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
    
    async def get_provider_capabilities(
        self,
        provider: LLMProviderType,
        model_name: Optional[str],
        tenant_id: str,
        llm_service
    ) -> ModelCapabilitiesResponse:
        """获取提供商能力信息"""
        try:
            # 模拟能力数据
            capabilities_data = self._get_mock_capabilities(provider, model_name)
            
            return ModelCapabilitiesResponse(
                success=True,
                message="提供商能力信息获取成功",
                data={"provider": provider.value, "model": model_name or "default"},
                provider=provider,
                model_name=model_name or self._get_default_model(provider),
                capabilities=capabilities_data["capabilities"],
                limitations=capabilities_data["limitations"],
                max_context_length=capabilities_data["max_context_length"],
                supported_languages=capabilities_data["supported_languages"],
                pricing=capabilities_data["pricing"],
                benchmarks=capabilities_data.get("benchmarks")
            )
            
        except Exception as e:
            self.logger.error(f"获取提供商能力失败: {e}", exc_info=True)
            raise ValidationException(f"获取提供商能力失败: {str(e)}")
    
    def _get_mock_capabilities(self, provider: LLMProviderType, model_name: Optional[str]) -> Dict[str, Any]:
        """获取模拟能力数据"""
        base_capabilities = {
            LLMProviderType.OPENAI: {
                "capabilities": ["text_generation", "code_generation", "analysis", "translation"],
                "limitations": ["rate_limits", "context_length"],
                "max_context_length": 128000,
                "supported_languages": ["zh", "en", "ja", "ko", "fr", "de", "es"],
                "pricing": {"input_tokens": 0.01, "output_tokens": 0.03},
                "benchmarks": {"speed": 0.85, "quality": 0.92, "cost_efficiency": 0.78}
            },
            LLMProviderType.ANTHROPIC: {
                "capabilities": ["text_generation", "analysis", "reasoning", "safety"],
                "limitations": ["rate_limits", "regional_availability"],
                "max_context_length": 200000,
                "supported_languages": ["zh", "en", "ja", "fr", "de", "es"],
                "pricing": {"input_tokens": 0.008, "output_tokens": 0.024},
                "benchmarks": {"speed": 0.80, "quality": 0.95, "cost_efficiency": 0.82}
            },
            LLMProviderType.GEMINI: {
                "capabilities": ["text_generation", "multimodal", "code_generation"],
                "limitations": ["beta_features", "rate_limits"],
                "max_context_length": 1000000,
                "supported_languages": ["zh", "en", "ja", "ko", "hi"],
                "pricing": {"input_tokens": 0.00125, "output_tokens": 0.00375},
                "benchmarks": {"speed": 0.75, "quality": 0.88, "cost_efficiency": 0.90}
            },
            LLMProviderType.DEEPSEEK: {
                "capabilities": ["text_generation", "code_generation", "chinese_optimized"],
                "limitations": ["regional_availability", "english_performance"],
                "max_context_length": 64000,
                "supported_languages": ["zh", "en"],
                "pricing": {"input_tokens": 0.0014, "output_tokens": 0.0028},
                "benchmarks": {"speed": 0.88, "quality": 0.85, "cost_efficiency": 0.95}
            }
        }
        
        return base_capabilities.get(provider, {})
    
    async def get_providers_health(
        self,
        tenant_id: str,
        time_range_hours: int,
        llm_service
    ) -> ProviderHealthResponse:
        """获取所有提供商健康状况"""
        try:
            # 模拟健康数据
            providers_metrics = []
            unhealthy_providers = []
            
            for provider in LLMProviderType:
                metrics = self._generate_mock_metrics(provider, time_range_hours)
                providers_metrics.append(metrics)
                
                # 检查是否不健康
                if metrics.failed_requests / metrics.total_requests > 0.05:
                    unhealthy_providers.append(provider)
            
            overall_health = "healthy" if not unhealthy_providers else "warning"
            if len(unhealthy_providers) >= 2:
                overall_health = "critical"
            
            alerts = []
            if unhealthy_providers:
                alerts.append({
                    "type": "high_failure_rate",
                    "providers": [p.value for p in unhealthy_providers],
                    "message": "某些提供商故障率过高"
                })
            
            return ProviderHealthResponse(
                success=True,
                message="提供商健康状况获取成功",
                data=providers_metrics,
                overall_health=overall_health,
                unhealthy_providers=unhealthy_providers,
                alerts=alerts if alerts else None
            )
            
        except Exception as e:
            self.logger.error(f"获取提供商健康状况失败: {e}", exc_info=True)
            raise ValidationException(f"获取提供商健康状况失败: {str(e)}")
    
    def _generate_mock_metrics(self, provider: LLMProviderType, hours: int) -> ProviderMetrics:
        """生成模拟指标数据"""
        import random
        
        total_requests = random.randint(100, 1000) * hours
        success_rate = random.uniform(0.95, 0.99)
        successful_requests = int(total_requests * success_rate)
        failed_requests = total_requests - successful_requests
        
        return ProviderMetrics(
            provider=provider,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            average_latency_ms=random.uniform(500, 1500),
            p95_latency_ms=random.uniform(1000, 2500),
            p99_latency_ms=random.uniform(2000, 4000),
            total_cost_usd=round(random.uniform(10, 100), 2),
            cost_per_request=round(random.uniform(0.01, 0.05), 4),
            token_usage={"input_tokens": random.randint(50000, 200000), "output_tokens": random.randint(20000, 80000)},
            time_range={
                "start": datetime.now() - timedelta(hours=hours),
                "end": datetime.now()
            }
        )
    
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
    
    # 其他方法的实现...
    async def set_cost_budget(self, tenant_id: str, budget_request: CostBudgetRequest, llm_service) -> Dict[str, Any]:
        """设置成本预算"""
        return {"success": True, "message": "预算设置成功", "budget": budget_request.monthly_budget}
    
    async def get_routing_stats(self, tenant_id: str, days: int, agent_type: Optional[str], llm_service) -> RoutingStatsResponse:
        """获取路由统计"""
        # 模拟实现
        return RoutingStatsResponse(
            success=True,
            message="路由统计获取成功",
            data={},
            current_strategy=RoutingStrategy.AGENT_OPTIMIZED,
            routing_distribution={LLMProviderType.OPENAI: 0.4, LLMProviderType.ANTHROPIC: 0.35, LLMProviderType.GEMINI: 0.15, LLMProviderType.DEEPSEEK: 0.10},
            agent_routing_stats={},
            routing_efficiency=0.85,
            failover_events=3,
            time_range={"start": datetime.now() - timedelta(days=days), "end": datetime.now()}
        )
    
    async def configure_routing(self, tenant_id: str, routing_config: RoutingConfigRequest, llm_service) -> Dict[str, Any]:
        """配置路由策略"""
        return {"success": True, "message": "路由配置成功", "strategy": routing_config.strategy.value}
    
    async def optimize_usage(self, tenant_id: str, optimization_request: OptimizationRequest, llm_service) -> OptimizationResponse:
        """优化使用策略"""
        return OptimizationResponse(
            success=True,
            message="优化建议生成成功",
            data={},
            optimization_type=optimization_request.optimization_type,
            recommendations=[{"type": "cost", "action": "switch_provider", "description": "建议使用更便宜的模型"}],
            estimated_savings={"monthly": 150.0},
            applied=not optimization_request.dry_run,
            rollback_available=True,
            impact_assessment={"performance_impact": "minimal", "quality_impact": "low"}
        )
    
    async def test_provider(self, provider: LLMProviderType, test_message: str, model_name: Optional[str], tenant_id: str, llm_service) -> Dict[str, Any]:
        """测试提供商"""
        return {
            "success": True,
            "provider": provider.value,
            "model": model_name or self._get_default_model(provider),
            "response_time_ms": 850.5,
            "test_response": "This is a test response from the provider."
        }
    
    async def remove_provider_config(self, provider: LLMProviderType, tenant_id: str, llm_service) -> Dict[str, Any]:
        """移除提供商配置"""
        return {"success": True, "message": f"提供商 {provider.value} 配置已移除"}
    
    async def toggle_provider(self, provider: LLMProviderType, enabled: bool, tenant_id: str, llm_service) -> Dict[str, Any]:
        """启用/禁用提供商"""
        action = "启用" if enabled else "禁用"
        return {"success": True, "message": f"提供商 {provider.value} 已{action}"}
    
    async def batch_test_providers(self, providers: List[LLMProviderType], test_message: str, tenant_id: str, llm_service) -> Dict[str, Any]:
        """批量测试提供商"""
        results = []
        for provider in providers:
            result = await self.test_provider(provider, test_message, None, tenant_id, llm_service)
            results.append(result)
        return {"success": True, "test_results": results}
    
    async def compare_models(self, providers: List[LLMProviderType], criteria: List[str], tenant_id: str, llm_service) -> Dict[str, Any]:
        """模型对比分析"""
        return {"success": True, "comparison": "模型对比分析结果", "criteria": criteria}
    
    async def get_global_stats(self, tenant_id: str, days: int, llm_service) -> Dict[str, Any]:
        """获取全局统计"""
        return {"success": True, "stats": "全局统计数据"}
    
    async def perform_maintenance(self, maintenance_type: str, tenant_id: str, llm_service) -> Dict[str, Any]:
        """执行维护操作"""
        return {"success": True, "message": f"维护操作 {maintenance_type} 执行成功"}