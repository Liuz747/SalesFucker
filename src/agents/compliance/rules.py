"""
合规规则模块 - 轻量级入口

该模块作为合规规则系统的主要入口，遵循模块化设计原则。
将原本臃肿的416行文件重构为多个专注的小模块。

核心功能:
- 导入规则相关组件
- 提供统一的接口
- 保持向后兼容性
"""

# 从各个专注模块导入组件
from .rule_types import ComplianceRule, RuleSeverity, RuleAction
from .default_rules import get_default_rules, get_rules_by_category, get_critical_rules
from .rule_manager import ComplianceRuleManager

# 向后兼容的别名
ComplianceRuleSet = ComplianceRuleManager

# 公开接口
__all__ = [
    "ComplianceRule",
    "RuleSeverity", 
    "RuleAction",
    "ComplianceRuleManager",
    "ComplianceRuleSet",  # 向后兼容
    "get_default_rules",
    "get_rules_by_category", 
    "get_critical_rules"
] 