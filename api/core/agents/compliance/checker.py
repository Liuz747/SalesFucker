"""
合规检查核心逻辑模块

该模块包含合规性检查的核心算法和规则处理逻辑。
从主智能体中分离出来，专注于违规检测和状态判断。

核心功能:
- 文本合规性检查
- 违规分析和分类
- 合规状态判断
- 用户友好消息生成
"""

from typing import Any
from datetime import datetime

from .rule_manager import ComplianceRuleManager


class ComplianceChecker:
    """
    合规检查器
    
    负责执行具体的合规性检查逻辑，包括违规检测、
    严重性分析和状态判断。独立于智能体主类运行。
    
    属性:
        rule_set: 合规规则集实例
        agent_id: 关联的智能体ID
    """
    
    def __init__(self, rule_set: ComplianceRuleManager, agent_id: str):
        """
        初始化合规检查器
        
        参数:
            rule_set: 合规规则集实例
            agent_id: 智能体标识符
        """
        self.rule_set = rule_set
        self.agent_id = agent_id
    
    async def perform_compliance_check(self, text: str) -> dict[str, Any]:
        """
        执行综合合规性检查
        
        使用规则集对输入文本进行全面的合规性分析，
        返回详细的检查结果和处理建议。
        
        参数:
            text: 待检查的文本内容
            
        返回:
            dict[str, Any]: 合规检查结果
        """
        if not text or not text.strip():
            return self._create_empty_result()
        
        # 使用规则集检查文本
        violations = self.rule_set.check_text(text)
        
        # 分析违规严重性
        highest_severity = self._determine_highest_severity(violations)
        
        # 确定处理状态
        status = self._determine_compliance_status(violations, highest_severity)
        
        # 生成用户消息
        user_message = self._generate_user_message(status, violations)
        
        # 构建完整结果
        return self._create_compliance_result(
            status, violations, highest_severity, user_message
        )
    
    def _create_empty_result(self) -> dict[str, Any]:
        """
        创建空文本的合规检查结果
        
        返回:
            dict[str, Any]: 空文本的检查结果
        """
        return {
            "status": "approved",
            "violations": [],
            "severity": "low",
            "user_message": "",
            "rules_checked": 0,
            "agent_id": self.agent_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _create_compliance_result(self, status: str, violations: list[dict[str, Any]], 
                                highest_severity: str, user_message: str) -> dict[str, Any]:
        """
        构建完整的合规检查结果
        
        参数:
            status: 合规状态
            violations: 违规信息列表
            highest_severity: 最高严重级别
            user_message: 用户消息
            
        返回:
            dict[str, Any]: 完整的检查结果
        """
        return {
            "status": status,
            "violations": violations,
            "severity": highest_severity,
            "user_message": user_message,
            "rules_checked": len(self.rule_set),
            "violation_count": len(violations),
            "categories_violated": list(set(v["category"] for v in violations)),
            "agent_id": self.agent_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _determine_highest_severity(self, violations: list[dict[str, Any]]) -> str:
        """
        确定违规的最高严重级别
        
        参数:
            violations: 违规信息列表
            
        返回:
            str: 最高严重级别
        """
        if not violations:
            return "low"
        
        severity_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        max_level = 0
        highest_severity = "low"
        
        for violation in violations:
            level = severity_levels.get(violation["severity"], 0)
            if level > max_level:
                max_level = level
                highest_severity = violation["severity"]
        
        return highest_severity
    
    def _determine_compliance_status(self, violations: list[dict[str, Any]], 
                                   highest_severity: str) -> str:
        """
        根据违规情况确定合规状态
        
        参数:
            violations: 违规信息列表
            highest_severity: 最高严重级别
            
        返回:
            str: 合规状态 (approved/flagged/blocked)
        """
        if not violations:
            return "approved"
        
        # 检查是否有阻止级别的违规
        for violation in violations:
            if violation["action"] == "block" or violation["severity"] == "critical":
                return "blocked"
        
        # 检查严重级别
        if highest_severity in ["high", "medium"]:
            return "flagged"
        
        return "approved"
    
    def _generate_user_message(self, status: str, violations: list[dict[str, Any]]) -> str:
        """
        根据合规状态生成用户友好的消息
        
        针对不同违规类型和严重级别生成相应的友好提示，
        确保用户体验的同时维护合规要求。
        
        参数:
            status: 合规状态
            violations: 违规信息列表
            
        返回:
            str: 用户友好的消息
        """
        if status == "approved":
            return ""
        
        elif status == "blocked":
            return self._generate_blocked_message(violations)
        
        elif status == "flagged":
            return ("我收到了您的消息，非常乐意为您提供帮助！"
                   "让我为您推荐最适合的美容产品。")
        
        return ""
    
    def _generate_blocked_message(self, violations: list[dict[str, Any]]) -> str:
        """
        生成阻止状态的用户消息
        
        参数:
            violations: 违规信息列表
            
        返回:
            str: 阻止状态的用户消息
        """
        # 针对不同违规类型提供具体的友好提示
        if any(v["category"] == "ingredient_safety" for v in violations):
            return ("为了您的安全，我们不能讨论某些成分。"
                   "让我为您推荐一些安全有效的美容产品吧！")
        elif any(v["category"] == "regulatory_fda" for v in violations):
            return ("我理解您对产品效果的关心。作为美容顾问，"
                   "我可以为您介绍产品的美容功效和使用体验。")
        else:
            return ("抱歉，我无法处理您的这个请求。"
                   "不过我很乐意为您推荐其他合适的美容解决方案！") 