"""
成本优化器模块

该模块实现了多LLM供应商的成本追踪、分析和优化功能。
提供实时成本监控、预算管理和智能成本优化建议。

核心功能:
- 实时成本追踪和计算
- 多维度成本分析和报告
- 预算管理和告警
- 智能成本优化策略
- 多租户成本隔离
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum

from .base_provider import LLMRequest, LLMResponse
from .provider_config import ProviderType, CostConfig
from .cost_optimizer_modules.models import CostRecord, CostAnalysis, OptimizationSuggestion, OptimizationType
from .cost_optimizer_modules.analyzer import CostAnalyzer
from .cost_optimizer_modules.suggestion_engine import SuggestionEngine
from .cost_optimizer_modules.budget_monitor import BudgetMonitor
from .cost_optimizer_modules.benchmark_data import BenchmarkData
from src.utils import get_component_logger, ErrorHandler




class CostOptimizer:
    """
    成本优化器类
    
    提供全面的成本追踪、分析和优化功能。
    支持多租户成本隔离和智能优化建议。
    """
    
    def __init__(self):
        """初始化成本优化器"""
        self.logger = get_component_logger(__name__, "CostOptimizer")
        self.error_handler = ErrorHandler("cost_optimizer")
        
        # 初始化核心组件
        self.analyzer = CostAnalyzer()
        self.suggestion_engine = SuggestionEngine()
        self.budget_monitor = BudgetMonitor()
        self.benchmark_data = BenchmarkData()
        
        # 成本记录存储
        self.cost_records: List[CostRecord] = []
        self.max_records = 100000  # 最大记录数
        
        # 成本配置
        self.cost_configs: Dict[str, CostConfig] = {}
        
        # 预算告警状态
        self.budget_alerts: Dict[str, Dict[str, bool]] = defaultdict(dict)
        
        # 成本分析缓存
        self.analysis_cache: Dict[str, Tuple[datetime, CostAnalysis]] = {}
        self.cache_ttl = timedelta(minutes=30)
        
        # 优化策略配置
        self.optimization_strategies = {
            OptimizationType.PROVIDER_SWITCH: {
                "min_savings_threshold": 0.2,  # 最小节省20%
                "confidence_threshold": 0.8,
                "evaluation_window": timedelta(hours=24)
            },
            OptimizationType.MODEL_DOWNGRADE: {
                "min_savings_threshold": 0.15,
                "confidence_threshold": 0.7,
                "quality_impact_threshold": 0.1  # 质量影响不超过10%
            },
            OptimizationType.CACHE_STRATEGY: {
                "min_cache_hit_rate": 0.3,
                "cache_cost_reduction": 0.9  # 缓存命中减少90%成本
            }
        }
        
        # 成本基准数据
        self.provider_benchmarks = {
            ProviderType.OPENAI: {
                "gpt-4": {"input": 0.03, "output": 0.06},
                "gpt-4-turbo": {"input": 0.01, "output": 0.03},
                "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015}
            },
            ProviderType.ANTHROPIC: {
                "claude-3-opus": {"input": 0.015, "output": 0.075},
                "claude-3-sonnet": {"input": 0.003, "output": 0.015},
                "claude-3-haiku": {"input": 0.00025, "output": 0.00125}
            },
            ProviderType.GEMINI: {
                "gemini-pro": {"input": 0.0005, "output": 0.0015},
                "gemini-pro-vision": {"input": 0.0005, "output": 0.0015}
            },
            ProviderType.DEEPSEEK: {
                "deepseek-chat": {"input": 0.0002, "output": 0.0002},
                "deepseek-coder": {"input": 0.0002, "output": 0.0002}
            }
        }
        
        self.logger.info("成本优化器初始化完成")
    
    async def record_cost(
        self,
        request: LLMRequest,
        response: LLMResponse,
        provider_type: ProviderType,
        agent_type: Optional[str] = None
    ):
        """
        记录请求成本
        
        参数:
            request: LLM请求对象
            response: LLM响应对象
            provider_type: 供应商类型
            agent_type: 智能体类型
        """
        try:
            # 提取令牌使用信息
            input_tokens = 0
            output_tokens = 0
            
            if hasattr(response, 'usage_tokens'):
                total_tokens = response.usage_tokens
                # 尝试从元数据中获取详细信息
                if 'usage_details' in response.metadata:
                    usage_details = response.metadata['usage_details']
                    input_tokens = usage_details.get('prompt_tokens', 0)
                    output_tokens = usage_details.get('completion_tokens', 0)
                else:
                    # 估算输入输出比例（通常输入占60%，输出占40%）
                    input_tokens = int(total_tokens * 0.6)
                    output_tokens = int(total_tokens * 0.4)
            else:
                total_tokens = len(response.content) // 4  # 粗略估算
                input_tokens = int(total_tokens * 0.6)
                output_tokens = int(total_tokens * 0.4)
            
            # 创建成本记录
            cost_record = CostRecord(
                request_id=request.request_id,
                provider_type=provider_type,
                model_name=response.model,
                agent_type=agent_type,
                tenant_id=request.tenant_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost=response.cost,
                timestamp=response.created_at,
                response_time=response.response_time,
                metadata={
                    "request_type": request.request_type.value,
                    "temperature": getattr(request, 'temperature', None),
                    "max_tokens": getattr(request, 'max_tokens', None)
                }
            )
            
            # 添加到记录列表
            self.cost_records.append(cost_record)
            
            # 清理旧记录
            if len(self.cost_records) > self.max_records:
                self.cost_records = self.cost_records[-self.max_records:]
            
            # 检查预算告警
            await self.budget_monitor.check_alerts(cost_record)
            
            # 清理相关缓存
            self._invalidate_analysis_cache(request.tenant_id)
            
            self.logger.debug(
                f"记录成本: {request.request_id}, "
                f"供应商: {provider_type}, "
                f"成本: ${response.cost:.6f}, "
                f"令牌: {total_tokens}"
            )
            
        except Exception as e:
            self.error_handler.handle_error(e, {
                "request_id": request.request_id,
                "provider_type": provider_type,
                "operation": "record_cost"
            })
    
    async def analyze_costs(
        self,
        tenant_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        use_cache: bool = True
    ) -> CostAnalysis:
        """
        分析成本数据
        
        参数:
            tenant_id: 租户ID，None表示全局分析
            start_time: 开始时间
            end_time: 结束时间
            use_cache: 是否使用缓存
            
        返回:
            CostAnalysis: 成本分析结果
        """
        # 设置默认时间范围（最近30天）
        if not end_time:
            end_time = datetime.now()
        if not start_time:
            start_time = end_time - timedelta(days=30)
        
        # 检查缓存
        cache_key = f"{tenant_id}_{start_time.isoformat()}_{end_time.isoformat()}"
        if use_cache and cache_key in self.analysis_cache:
            cached_time, cached_analysis = self.analysis_cache[cache_key]
            if datetime.now() - cached_time < self.cache_ttl:
                return cached_analysis
        
        try:
            # 过滤相关记录
            filtered_records = self._filter_records(
                tenant_id=tenant_id,
                start_time=start_time,
                end_time=end_time
            )
            
            if not filtered_records:
                return CostAnalysis(
                    period_start=start_time,
                    period_end=end_time,
                    total_cost=0.0,
                    total_requests=0,
                    total_tokens=0,
                    avg_cost_per_request=0.0,
                    avg_cost_per_token=0.0,
                    provider_breakdown={},
                    agent_breakdown={},
                    tenant_breakdown={},
                    cost_trends={},
                    optimization_opportunities=[]
                )
            
            # 计算基础统计
            total_cost = sum(record.cost for record in filtered_records)
            total_requests = len(filtered_records)
            total_tokens = sum(record.total_tokens for record in filtered_records)
            
            avg_cost_per_request = total_cost / total_requests if total_requests > 0 else 0
            avg_cost_per_token = total_cost / total_tokens if total_tokens > 0 else 0
            
            # 供应商成本分解
            provider_breakdown = defaultdict(float)
            for record in filtered_records:
                provider_breakdown[record.provider_type.value] += record.cost
            
            # 智能体成本分解
            agent_breakdown = defaultdict(float)
            for record in filtered_records:
                if record.agent_type:
                    agent_breakdown[record.agent_type] += record.cost
            
            # 租户成本分解
            tenant_breakdown = defaultdict(float)
            for record in filtered_records:
                tenant_key = record.tenant_id or "default"
                tenant_breakdown[tenant_key] += record.cost
            
            # 成本趋势分析
            cost_trends = self.analyzer.calculate_trends(filtered_records, start_time, end_time)
            
            # 优化机会分析
            optimization_opportunities = await self.analyzer.identify_opportunities(filtered_records)
            
            # 创建分析结果
            analysis = CostAnalysis(
                period_start=start_time,
                period_end=end_time,
                total_cost=total_cost,
                total_requests=total_requests,
                total_tokens=total_tokens,
                avg_cost_per_request=avg_cost_per_request,
                avg_cost_per_token=avg_cost_per_token,
                provider_breakdown=dict(provider_breakdown),
                agent_breakdown=dict(agent_breakdown),
                tenant_breakdown=dict(tenant_breakdown),
                cost_trends=cost_trends,
                optimization_opportunities=optimization_opportunities
            )
            
            # 缓存结果
            self.analysis_cache[cache_key] = (datetime.now(), analysis)
            
            self.logger.info(
                f"成本分析完成: 租户={tenant_id}, "
                f"总成本=${total_cost:.4f}, "
                f"请求数={total_requests}, "
                f"优化机会={len(optimization_opportunities)}"
            )
            
            return analysis
            
        except Exception as e:
            self.error_handler.handle_error(e, {
                "tenant_id": tenant_id,
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None,
                "operation": "analyze_costs"
            })
            raise
    
    async def get_optimization_suggestions(
        self,
        tenant_id: Optional[str] = None,
        min_savings: float = 0.1
    ) -> List[OptimizationSuggestion]:
        """
        获取成本优化建议
        
        参数:
            tenant_id: 租户ID
            min_savings: 最小节省比例
            
        返回:
            List[OptimizationSuggestion]: 优化建议列表
        """
        try:
            # 获取最近的成本分析
            analysis = await self.analyze_costs(tenant_id=tenant_id)
            
            suggestions = []
            
            # 供应商切换建议
            provider_suggestions = await self.suggestion_engine.analyze_provider_switching(analysis, min_savings)
            suggestions.extend(provider_suggestions)
            
            # 模型降级建议
            model_suggestions = await self.suggestion_engine.analyze_model_downgrading(analysis, min_savings)
            suggestions.extend(model_suggestions)
            
            # 缓存策略建议
            cache_suggestions = await self.suggestion_engine.analyze_cache_opportunities(analysis, min_savings)
            suggestions.extend(cache_suggestions)
            
            # 按节省潜力排序
            suggestions.sort(key=lambda x: x.potential_savings, reverse=True)
            
            self.logger.info(f"生成优化建议: {len(suggestions)} 条, 租户: {tenant_id}")
            
            return suggestions
            
        except Exception as e:
            self.error_handler.handle_error(e, {
                "tenant_id": tenant_id,
                "min_savings": min_savings,
                "operation": "get_optimization_suggestions"
            })
            return []
    
    def _filter_records(
        self,
        tenant_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        provider_type: Optional[ProviderType] = None,
        agent_type: Optional[str] = None
    ) -> List[CostRecord]:
        """过滤成本记录"""
        filtered = self.cost_records
        
        if tenant_id is not None:
            filtered = [r for r in filtered if r.tenant_id == tenant_id]
        
        if start_time:
            filtered = [r for r in filtered if r.timestamp >= start_time]
        
        if end_time:
            filtered = [r for r in filtered if r.timestamp <= end_time]
        
        if provider_type:
            filtered = [r for r in filtered if r.provider_type == provider_type]
        
        if agent_type:
            filtered = [r for r in filtered if r.agent_type == agent_type]
        
        return filtered
    
    def _create_cost_record(
        self, 
        request: LLMRequest, 
        response: LLMResponse, 
        provider_type: ProviderType, 
        agent_type: Optional[str]
    ) -> CostRecord:
        """创建成本记录"""
        # 提取令牌使用信息
        input_tokens = 0
        output_tokens = 0
        
        if hasattr(response, 'usage_tokens'):
            total_tokens = response.usage_tokens
            if 'usage_details' in response.metadata:
                usage_details = response.metadata['usage_details']
                input_tokens = usage_details.get('prompt_tokens', 0)
                output_tokens = usage_details.get('completion_tokens', 0)
            else:
                input_tokens = int(total_tokens * 0.6)
                output_tokens = int(total_tokens * 0.4)
        else:
            total_tokens = len(response.content) // 4
            input_tokens = int(total_tokens * 0.6)
            output_tokens = int(total_tokens * 0.4)
        
        return CostRecord(
            request_id=request.request_id,
            provider_type=provider_type,
            model_name=response.model,
            agent_type=agent_type,
            tenant_id=request.tenant_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost=response.cost,
            timestamp=response.created_at,
            response_time=response.response_time,
            metadata={
                "request_type": request.request_type.value,
                "temperature": getattr(request, 'temperature', None),
                "max_tokens": getattr(request, 'max_tokens', None)
            }
        )
    
    def _invalidate_analysis_cache(self, tenant_id: Optional[str]):
        """清理分析缓存"""
        keys_to_remove = []
        for key in self.analysis_cache.keys():
            if tenant_id is None or key.startswith(f"{tenant_id}_"):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.analysis_cache[key]
    
    def set_cost_config(self, tenant_id: str, cost_config: CostConfig):
        """设置租户成本配置"""
        self.cost_configs[tenant_id] = cost_config
        self.budget_monitor.reset_alerts(tenant_id)
        self.logger.info(f"更新租户成本配置: {tenant_id}")
    
    def get_cost_summary(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """获取成本摘要"""
        now = datetime.now()
        periods = {
            "24h": now - timedelta(hours=24),
            "7d": now - timedelta(days=7),
            "30d": now - timedelta(days=30)
        }
        
        summary = {}
        for period_name, start_time in periods.items():
            period_records = self._filter_records(
                tenant_id=tenant_id,
                start_time=start_time,
                end_time=now
            )
            
            summary[period_name] = {
                "total_cost": sum(r.cost for r in period_records),
                "total_requests": len(period_records),
                "total_tokens": sum(r.total_tokens for r in period_records),
                "avg_cost_per_request": (sum(r.cost for r in period_records) / 
                                       len(period_records)) if period_records else 0
            }
        
        return summary