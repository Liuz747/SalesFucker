"""
合规规则类型定义模块

该模块定义合规检查规则的基础类型、枚举和数据结构。
专注于类型定义，保持模块精简专一。

核心功能:
- 规则严重级别枚举
- 规则处理动作枚举
- 合规规则数据类定义
"""

import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class RuleSeverity(Enum):
    """
    规则严重级别枚举
    
    定义合规检查规则的严重程度分级，用于确定处理策略。
    """
    LOW = "low"         # 低：提醒级别，记录但不阻止
    MEDIUM = "medium"   # 中：警告级别，标记需要注意
    HIGH = "high"       # 高：严重级别，需要人工审核
    CRITICAL = "critical"  # 严重：阻止级别，立即阻止处理


class RuleAction(Enum):
    """
    规则处理动作枚举
    
    定义规则触发后的处理动作类型。
    """
    APPROVE = "approve"     # 批准：内容合规，继续处理
    FLAG = "flag"          # 标记：内容可疑，需要额外关注
    BLOCK = "block"        # 阻止：内容违规，禁止继续处理
    ESCALATE = "escalate"  # 升级：转交人工处理


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
    category: str = "general"
    tags: List[str] = None
    
    def __post_init__(self):
        """初始化后处理，编译正则表达式"""
        if self.tags is None:
            self.tags = []
        try:
            self.compiled_pattern = re.compile(self.pattern, re.IGNORECASE)
        except re.error as e:
            raise ValueError(f"无效的正则表达式模式: {self.pattern}, 错误: {e}")
    
    def check(self, text: str) -> Optional[Dict[str, Any]]:
        """
        检查文本是否违反此规则
        
        参数:
            text: 要检查的文本
            
        返回:
            Optional[Dict[str, Any]]: 如果违规则返回违规信息，否则返回None
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
                "category": self.category,
                "tags": self.tags
            }
        
        return None 