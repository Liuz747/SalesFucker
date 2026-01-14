"""
合规模块数据模型

该模块定义合规功能的数据模型和业务逻辑类。
专注于业务行为实现，保持职责清晰。

核心功能:
- 合规规则数据模型
- 规则匹配逻辑实现
- 违规检测算法
"""

from dataclasses import dataclass
import re
from typing import Any, Optional

from .types import RuleSeverity, RuleAction, RuleCategory


@dataclass
class ComplianceRule:
    """
    合规规则数据类
    
    定义单个合规检查规则的所有属性和行为。
    支持正则表达式模式匹配和多种处理策略。
    
    属性:
        rule_id: 规则唯一标识符
        name: 规则名称
        description: 规则描述
        pattern: 正则表达式模式
        severity: 严重级别
        action: 处理动作
        message: 违规提示消息
        tenant_specific: 是否为租户特定规则
        enabled: 规则是否启用
        category: 规则分类
        tags: 规则标签
    """
    
    rule_id: str
    name: str
    description: str
    pattern: str
    severity: RuleSeverity
    action: RuleAction
    message: str
    tenant_specific: bool = False
    enabled: bool = True
    category: RuleCategory = RuleCategory.CONTENT
    tags: list[str] = None
    
    def __post_init__(self):
        """初始化后处理，编译正则表达式"""
        if self.tags is None:
            self.tags = []
        try:
            self.compiled_pattern = re.compile(self.pattern, re.IGNORECASE)
        except re.error as e:
            raise ValueError(f"无效的正则表达式模式: {self.pattern}, 错误: {e}")
    
    def check(self, text: str) -> Optional[dict[str, Any]]:
        """
        检查文本是否违反此规则
        
        参数:
            text: 要检查的文本
            
        返回:
            Optional[dict[str, Any]]: 如果违规则返回违规信息，否则返回None
        """
        if not self.enabled:
            return None
        
        match = self.compiled_pattern.search(text)
        if match:
            return {
                "rule_id": self.rule_id,
                "rule_name": self.name,
                "severity": self.severity.value,
                "action": self.action.value,
                "message": self.message,
                "matched_text": match.group(),
                "match_position": match.span(),
                "category": self.category.value,
                "tags": self.tags
            }
        
        return None
    
    def is_critical(self) -> bool:
        """判断规则是否为严重级别"""
        return self.severity == RuleSeverity.CRITICAL
    
    def should_block(self) -> bool:
        """判断规则是否应该阻止处理"""
        return self.action in [RuleAction.BLOCK, RuleAction.ESCALATE] 