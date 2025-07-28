"""
默认合规规则定义模块

该模块包含化妆品行业的默认合规检查规则。
分离规则数据定义，便于维护和扩展。

核心功能:
- FDA化妆品法规规则
- EU化妆品法规规则
- 成分安全检查规则
- 隐私保护规则
- 竞品检测规则
"""

from typing import List
from .rule_types import ComplianceRule, RuleSeverity, RuleAction


def get_default_rules() -> List[ComplianceRule]:
    """
    获取默认合规规则列表
    
    返回:
        List[ComplianceRule]: 默认规则列表
    """
    return [
        # FDA化妆品法规
        ComplianceRule(
            rule_id="fda_drug_claims",
            name="FDA药物功效声明",
            description="检测可能违反FDA化妆品法规的药物功效声明",
            pattern=r"\b(cure|heal|treat|prevent|drug|medicine|therapeutic)\b",
            severity=RuleSeverity.CRITICAL,
            action=RuleAction.BLOCK,
            message="检测到可能的药物功效声明，违反FDA化妆品法规",
            category="fda_compliance",
            tags=["fda", "drug_claims", "cosmetics"]
        ),
        
        # EU化妆品法规
        ComplianceRule(
            rule_id="eu_cosmetics_regulation",
            name="EU化妆品法规",
            description="检测违反EU化妆品法规1223/2009的内容",
            pattern=r"\b(miracle|fountain of youth|anti-aging breakthrough|永久|奇迹|逆转衰老)\b",
            severity=RuleSeverity.HIGH,
            action=RuleAction.FLAG,
            message="检测到可能违反EU化妆品法规的夸大声明",
            category="eu_compliance",
            tags=["eu", "cosmetics", "regulation"]
        ),
        
        # 成分安全检查
        ComplianceRule(
            rule_id="banned_ingredients",
            name="禁用成分检测",
            description="检测化妆品中的禁用或危险成分",
            pattern=r"\b(mercury|lead|arsenic|formaldehyde|hydroquinone|汞|铅|砷|甲醛|对苯二酚)\b",
            severity=RuleSeverity.CRITICAL,
            action=RuleAction.BLOCK,
            message="检测到危险或被禁成分",
            category="ingredient_safety",
            tags=["banned", "dangerous", "ingredients"]
        ),
        
        # 垃圾邮件检测
        ComplianceRule(
            rule_id="spam_detection",
            name="垃圾信息检测",
            description="检测垃圾邮件和恶意推广内容",
            pattern=r"(click here|visit now|limited time|act now|make money|buy now)",
            severity=RuleSeverity.MEDIUM,
            action=RuleAction.FLAG,
            message="检测到可能的垃圾推广内容",
            category="spam_protection",
            tags=["spam", "promotion"]
        ),
        
        # 个人信息保护
        ComplianceRule(
            rule_id="personal_info",
            name="个人信息检测",
            description="检测可能的个人敏感信息泄露",
            pattern=r"\b(\d{3}[-.]?\d{2}[-.]?\d{4}|\d{16}|\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b)\b",
            severity=RuleSeverity.HIGH,
            action=RuleAction.FLAG,
            message="检测到个人信息，需要隐私保护",
            category="privacy_protection",
            tags=["privacy", "personal_info"]
        ),
        
        # 竞品提及（租户特定）
        ComplianceRule(
            rule_id="competitor_mention",
            name="竞品提及检测",
            description="检测竞争对手品牌提及",
            pattern=r"\b(sephora|ulta|mac|maybelline|loreal|revlon|covergirl)\b",
            severity=RuleSeverity.LOW,
            action=RuleAction.FLAG,
            message="检测到竞争品牌提及",
            category="competitive_intelligence",
            tags=["competitor", "brand"],
            tenant_specific=True
        ),
        
        # 年龄限制声明
        ComplianceRule(
            rule_id="age_restrictions",
            name="年龄限制检测",
            description="检测需要年龄限制的产品声明",
            pattern=r"\b(under 18|children|kids|baby|infant|minors|18岁以下|儿童|婴儿|未成年)\b",
            severity=RuleSeverity.MEDIUM,
            action=RuleAction.FLAG,
            message="检测到涉及年龄限制的内容",
            category="age_compliance",
            tags=["age", "children", "restrictions"]
        ),
        
        # 医疗建议声明
        ComplianceRule(
            rule_id="medical_advice",
            name="医疗建议检测",
            description="检测可能构成医疗建议的内容",
            pattern=r"\b(doctor recommend|medical grade|clinically proven|dermatologist|医生推荐|医疗级|临床验证|皮肤科医生)\b",
            severity=RuleSeverity.HIGH,
            action=RuleAction.FLAG,
            message="检测到可能的医疗建议声明",
            category="medical_compliance",
            tags=["medical", "advice", "clinical"]
        )
    ]


def get_rules_by_category(category: str) -> List[ComplianceRule]:
    """
    根据分类获取规则
    
    参数:
        category: 规则分类
        
    返回:
        List[ComplianceRule]: 指定分类的规则列表
    """
    return [rule for rule in get_default_rules() if rule.category == category]


def get_critical_rules() -> List[ComplianceRule]:
    """
    获取严重级别的规则
    
    返回:
        List[ComplianceRule]: 严重级别规则列表
    """
    return [rule for rule in get_default_rules() if rule.severity == RuleSeverity.CRITICAL] 