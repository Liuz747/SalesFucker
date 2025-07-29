"""
合规审查模块

该包提供合规审查相关的所有功能，采用模块化设计。
包括合规检查、审计日志、性能指标和规则管理。

模块组织:
- agent: 合规审查智能体主类
- checker: 合规检查核心逻辑
- audit: 审计日志和报告
- metrics: 性能指标管理
- rules: 合规规则集管理
- models: 合规数据模型和业务逻辑
- types: 合规类型定义和枚举
"""

from .agent import ComplianceAgent
from .checker import ComplianceChecker
from .audit import ComplianceAuditor
from .metrics import ComplianceMetricsManager
from .rule_manager import ComplianceRuleManager
from .models import ComplianceRule
from .types import RuleSeverity, RuleAction, RuleCategory
from .default_rules import get_default_rules, get_rules_by_category, get_critical_rules

__all__ = [
    # 主要智能体类
    "ComplianceAgent",
    
    # 模块化组件
    "ComplianceChecker",
    "ComplianceAuditor", 
    "ComplianceMetricsManager",
    
    # 规则相关类
    "ComplianceRule",
    "ComplianceRuleManager", 
    "RuleSeverity",
    "RuleAction",
    "RuleCategory",
    
    # 规则函数
    "get_default_rules",
    "get_rules_by_category",
    "get_critical_rules"
] 