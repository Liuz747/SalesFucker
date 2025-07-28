"""
合规规则管理模块

该模块负责规则集合的管理、操作和查询功能。
专注于规则管理逻辑，保持功能单一。

核心功能:
- 规则集合管理
- 规则增删改查
- 规则分类和索引
- 规则统计信息
"""

from typing import Dict, Any, List, Optional
from .rule_types import ComplianceRule, RuleSeverity
from .default_rules import get_default_rules


class ComplianceRuleManager:
    """
    合规规则管理器
    
    负责管理合规规则的集合，提供规则的增删改查功能。
    支持分类管理和统计查询。
    
    属性:
        rules: 规则字典，按rule_id索引
        categories: 分类索引，按category分组
    """
    
    def __init__(self):
        """初始化规则管理器"""
        self.rules: Dict[str, ComplianceRule] = {}
        self.categories: Dict[str, List[str]] = {}
        self._load_default_rules()
    
    def _load_default_rules(self):
        """加载默认规则"""
        default_rules = get_default_rules()
        for rule in default_rules:
            self.add_rule(rule)
    
    def add_rule(self, rule: ComplianceRule) -> bool:
        """
        添加新的合规规则
        
        参数:
            rule: 要添加的规则对象
            
        返回:
            bool: 添加是否成功
        """
        if rule.rule_id in self.rules:
            return False
        
        self.rules[rule.rule_id] = rule
        
        # 更新分类索引
        if rule.category not in self.categories:
            self.categories[rule.category] = []
        self.categories[rule.category].append(rule.rule_id)
        
        return True
    
    def remove_rule(self, rule_id: str) -> bool:
        """
        移除合规规则
        
        参数:
            rule_id: 要移除的规则ID
            
        返回:
            bool: 移除是否成功
        """
        if rule_id not in self.rules:
            return False
        
        rule = self.rules[rule_id]
        
        # 从分类索引中移除
        if rule.category in self.categories:
            self.categories[rule.category].remove(rule_id)
            if not self.categories[rule.category]:
                del self.categories[rule.category]
        
        del self.rules[rule_id]
        return True
    
    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新规则属性
        
        参数:
            rule_id: 规则ID
            updates: 要更新的属性字典
            
        返回:
            bool: 更新是否成功
        """
        if rule_id not in self.rules:
            return False
        
        rule = self.rules[rule_id]
        
        # 更新允许的属性
        updatable_fields = ['enabled', 'severity', 'action', 'message']
        for field, value in updates.items():
            if field in updatable_fields and hasattr(rule, field):
                setattr(rule, field, value)
        
        return True
    
    def get_rule(self, rule_id: str) -> Optional[ComplianceRule]:
        """
        获取指定规则
        
        参数:
            rule_id: 规则ID
            
        返回:
            Optional[ComplianceRule]: 规则对象或None
        """
        return self.rules.get(rule_id)
    
    def get_enabled_rules(self) -> List[ComplianceRule]:
        """
        获取所有启用的规则
        
        返回:
            List[ComplianceRule]: 启用的规则列表
        """
        return [rule for rule in self.rules.values() if rule.enabled]
    
    def get_rules_by_category(self, category: str) -> List[ComplianceRule]:
        """
        根据分类获取规则
        
        参数:
            category: 规则分类
            
        返回:
            List[ComplianceRule]: 指定分类的规则列表
        """
        rule_ids = self.categories.get(category, [])
        return [self.rules[rule_id] for rule_id in rule_ids]
    
    def get_rules_by_severity(self, severity: RuleSeverity) -> List[ComplianceRule]:
        """
        根据严重级别获取规则
        
        参数:
            severity: 严重级别
            
        返回:
            List[ComplianceRule]: 指定严重级别的规则列表
        """
        return [rule for rule in self.rules.values() if rule.severity == severity]
    
    def check_text(self, text: str, categories: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        检查文本是否违反规则
        
        参数:
            text: 要检查的文本
            categories: 可选的规则分类过滤
            
        返回:
            List[Dict[str, Any]]: 违规信息列表
        """
        violations = []
        
        # 确定要检查的规则
        rules_to_check = self.get_enabled_rules()
        
        if categories:
            rules_to_check = [
                rule for rule in rules_to_check
                if rule.category in categories
            ]
        
        # 执行检查
        for rule in rules_to_check:
            violation = rule.check(text)
            if violation:
                violations.append(violation)
        
        return violations
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取规则集统计信息
        
        返回:
            Dict[str, Any]: 统计信息
        """
        enabled_count = sum(1 for rule in self.rules.values() if rule.enabled)
        
        severity_stats = {}
        for severity in RuleSeverity:
            severity_stats[severity.value] = sum(
                1 for rule in self.rules.values() 
                if rule.severity == severity
            )
        
        category_stats = {
            category: len(rule_ids)
            for category, rule_ids in self.categories.items()
        }
        
        return {
            "total_rules": len(self.rules),
            "enabled_rules": enabled_count,
            "disabled_rules": len(self.rules) - enabled_count,
            "categories": list(self.categories.keys()),
            "category_distribution": category_stats,
            "severity_distribution": severity_stats
        }
    
    def __len__(self) -> int:
        """返回规则总数"""
        return len(self.rules)
    
    def __contains__(self, rule_id: str) -> bool:
        """检查规则是否存在"""
        return rule_id in self.rules 