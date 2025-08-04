"""
预算监控模块

负责预算告警和监控功能。
"""

from typing import Dict, Any
from datetime import datetime, time
from collections import defaultdict

from .models import CostRecord
from ..provider_config import CostConfig
from src.utils import get_component_logger


class BudgetMonitor:
    """预算监控器类"""
    
    def __init__(self):
        """初始化预算监控器"""
        self.logger = get_component_logger(__name__, "BudgetMonitor")
        self.budget_alerts: Dict[str, Dict[str, bool]] = defaultdict(dict)
    
    async def check_budget_alerts(
        self,
        cost_record: CostRecord,
        cost_configs: Dict[str, CostConfig]
    ):
        """检查预算告警"""
        tenant_id = cost_record.tenant_id or "default"
        
        if tenant_id not in cost_configs:
            return
        
        cost_config = cost_configs[tenant_id]
        
        # 计算当日成本
        today_cost = self._calculate_daily_cost(cost_record, cost_configs)
        
        # 检查日预算告警
        await self._check_daily_budget_alerts(
            tenant_id, today_cost, cost_config
        )
    
    def _calculate_daily_cost(
        self,
        cost_record: CostRecord,
        cost_configs: Dict[str, CostConfig]
    ) -> float:
        """计算当日成本"""
        # 这里应该从外部数据源获取当日所有记录
        # 为简化示例，返回估算值
        return cost_record.cost * 100  # 估算
    
    async def _check_daily_budget_alerts(
        self,
        tenant_id: str,
        today_cost: float,
        cost_config: CostConfig
    ):
        """检查日预算告警"""
        if not cost_config.daily_budget or cost_config.daily_budget <= 0:
            return
        
        usage_ratio = today_cost / cost_config.daily_budget
        
        # 严重告警
        if usage_ratio >= cost_config.cost_threshold_critical:
            if not self.budget_alerts[tenant_id].get("daily_critical", False):
                self.logger.warning(
                    f"租户 {tenant_id} 日预算严重告警: "
                    f"${today_cost:.4f} / ${cost_config.daily_budget:.4f} "
                    f"({usage_ratio*100:.1f}%)"
                )
                self.budget_alerts[tenant_id]["daily_critical"] = True
        
        # 警告告警
        elif usage_ratio >= cost_config.cost_threshold_warning:
            if not self.budget_alerts[tenant_id].get("daily_warning", False):
                self.logger.info(
                    f"租户 {tenant_id} 日预算警告: "
                    f"${today_cost:.4f} / ${cost_config.daily_budget:.4f} "
                    f"({usage_ratio*100:.1f}%)"
                )
                self.budget_alerts[tenant_id]["daily_warning"] = True
    
    def reset_alerts(self, tenant_id: str):
        """重置告警状态"""
        self.budget_alerts[tenant_id] = {}
    
    def get_alert_status(self, tenant_id: str) -> Dict[str, bool]:
        """获取告警状态"""
        return self.budget_alerts.get(tenant_id, {}).copy()