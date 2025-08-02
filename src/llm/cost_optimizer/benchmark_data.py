"""
基准数据模块

提供供应商和模型的成本基准数据。
"""

from typing import Dict, List, Any

from ..provider_config import ProviderType


class BenchmarkData:
    """基准数据管理器类"""
    
    def __init__(self):
        """初始化基准数据"""
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
    
    def find_cheaper_alternatives(self, current_provider: str) -> List[Dict[str, Any]]:
        """寻找更便宜的替代供应商"""
        alternatives = []
        
        try:
            current_provider_type = ProviderType(current_provider)
            current_benchmarks = self.provider_benchmarks.get(current_provider_type, {})
            
            for provider_type, benchmarks in self.provider_benchmarks.items():
                if provider_type.value == current_provider:
                    continue
                
                # 计算平均成本差异
                if current_benchmarks and benchmarks:
                    current_avg_cost = self._calculate_average_cost(current_benchmarks)
                    alternative_avg_cost = self._calculate_average_cost(benchmarks)
                    
                    if alternative_avg_cost < current_avg_cost:
                        savings_rate = (current_avg_cost - alternative_avg_cost) / current_avg_cost
                        alternatives.append({
                            "provider": provider_type.value,
                            "savings_rate": savings_rate,
                            "confidence": 0.8,
                            "quality_impact": 0.05,
                            "response_time_impact": 0.1
                        })
        except ValueError:
            # 无效的供应商类型
            pass
        
        return alternatives
    
    def _calculate_average_cost(self, benchmarks: Dict[str, Dict[str, float]]) -> float:
        """计算供应商的平均成本"""
        total_cost = 0.0
        count = 0
        
        for model_costs in benchmarks.values():
            # 假设输入输出比例1:1
            avg_cost = (model_costs.get("input", 0) + model_costs.get("output", 0)) / 2
            total_cost += avg_cost
            count += 1
        
        return total_cost / count if count > 0 else 0.0
    
    def get_model_cost(self, provider_type: ProviderType, model_name: str) -> Dict[str, float]:
        """获取特定模型的成本信息"""
        provider_benchmarks = self.provider_benchmarks.get(provider_type, {})
        return provider_benchmarks.get(model_name, {"input": 0.0, "output": 0.0})
    
    def update_benchmark(
        self,
        provider_type: ProviderType,
        model_name: str,
        input_cost: float,
        output_cost: float
    ):
        """更新基准数据"""
        if provider_type not in self.provider_benchmarks:
            self.provider_benchmarks[provider_type] = {}
        
        self.provider_benchmarks[provider_type][model_name] = {
            "input": input_cost,
            "output": output_cost
        }