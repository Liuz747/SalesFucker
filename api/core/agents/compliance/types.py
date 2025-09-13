"""
合规模块类型定义

该模块定义合规功能专用的类型和枚举。
遵循域驱动设计原则，保持类型定义的内聚性。

核心功能:
- 合规规则严重级别枚举
- 合规规则处理动作枚举
- 合规相关的基础类型定义
"""

from enum import Enum


class RuleSeverity(str, Enum):
    """
    规则严重级别枚举
    
    定义合规检查规则的严重程度分级，用于确定处理策略。
    """
    LOW = "low"         # 低：提醒级别，记录但不阻止
    MEDIUM = "medium"   # 中：警告级别，标记需要注意
    HIGH = "high"       # 高：严重级别，需要人工审核
    CRITICAL = "critical"  # 严重：阻止级别，立即阻止处理


class RuleAction(str, Enum):
    """
    规则处理动作枚举
    
    定义规则触发后的处理动作类型。
    """
    APPROVE = "approve"     # 批准：内容合规，继续处理
    FLAG = "flag"          # 标记：内容可疑，需要额外关注
    BLOCK = "block"        # 阻止：内容违规，禁止继续处理
    ESCALATE = "escalate"  # 升级：转交人工处理


class RuleCategory(str, Enum):
    """
    规则分类枚举
    
    定义合规规则的分类类型，便于规则管理和组织。
    """
    CONTENT = "content"         # 内容规则：检查消息内容
    PRIVACY = "privacy"         # 隐私规则：保护用户隐私
    SAFETY = "safety"          # 安全规则：防止有害内容
    REGULATORY = "regulatory"   # 法规规则：符合法律法规
    BUSINESS = "business"      # 业务规则：符合业务策略 