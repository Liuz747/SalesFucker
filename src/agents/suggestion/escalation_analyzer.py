"""
升级分析器

处理人工升级决策和规则评估。
负责分析是否需要人工干预的核心logic。
"""

from typing import Dict, Any, List
import logging
from utils import get_component_logger


class EscalationAnalyzer:
    """
    升级分析器
    
    负责分析对话和系统状态，决定是否需要人工升级。
    使用规则引擎和置信度计算提供升级建议。
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.logger = get_component_logger(f"escalation_analyzer_{tenant_id}")
        
        # 升级规则配置
        self.escalation_rules = {
            "complexity_threshold": 0.8,
            "confidence_threshold": 0.6,
            "sentiment_escalation": ["negative"],
            "compliance_escalation": ["blocked", "flagged"],
            "intent_escalation": ["complaint", "refund", "technical_issue"]
        }
        
        self.logger.info(f"升级分析器初始化完成: tenant_id={tenant_id}")
    
    async def analyze_escalation_need(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析是否需要人工升级
        
        参数:
            context_data: 上下文数据
            
        返回:
            Dict[str, Any]: 升级分析结果
        """
        try:
            escalation_factors = []
            escalation_score = 0.0
            
            # 检查情感因素
            escalation_score += self._analyze_sentiment_factors(
                context_data.get("sentiment", {}), escalation_factors
            )
            
            # 检查合规因素
            escalation_score += self._analyze_compliance_factors(
                context_data.get("compliance", {}), escalation_factors
            )
            
            # 检查意图因素
            escalation_score += self._analyze_intent_factors(
                context_data.get("intent", {}), escalation_factors
            )
            
            # 检查对话复杂度
            escalation_score += self._analyze_complexity_factors(
                context_data, escalation_factors
            )
            
            # 检查代理响应质量
            escalation_score += self._analyze_agent_quality_factors(
                context_data.get("agent_responses", {}), escalation_factors
            )
            
            # 决定是否升级
            escalation_recommended = escalation_score >= 0.5
            
            return {
                "escalation_recommended": escalation_recommended,
                "escalation_score": min(1.0, escalation_score),
                "escalation_factors": escalation_factors,
                "confidence": self._calculate_escalation_confidence(context_data),
                "suggested_action": "human_handoff" if escalation_recommended else "continue_ai",
                "rule_based_analysis": True
            }
            
        except Exception as e:
            self.logger.error(f"升级分析失败: {e}")
            return self._get_fallback_escalation_result(str(e))
    
    def _analyze_sentiment_factors(self, sentiment_data: Dict[str, Any], 
                                 escalation_factors: List[str]) -> float:
        """分析情感因素对升级的影响"""
        if sentiment_data.get("sentiment") in self.escalation_rules["sentiment_escalation"]:
            escalation_factors.append("Negative customer sentiment detected")
            
            # 考虑情感强度
            confidence = sentiment_data.get("confidence", 0.5)
            return 0.3 * confidence
        
        return 0.0
    
    def _analyze_compliance_factors(self, compliance_data: Dict[str, Any], 
                                  escalation_factors: List[str]) -> float:
        """分析合规因素对升级的影响"""
        if compliance_data.get("status") in self.escalation_rules["compliance_escalation"]:
            escalation_factors.append("Compliance issues detected")
            
            # 合规问题通常需要立即升级
            severity = compliance_data.get("severity", "medium")
            severity_multiplier = {"low": 0.2, "medium": 0.4, "high": 0.6}.get(severity, 0.4)
            
            return severity_multiplier
        
        return 0.0
    
    def _analyze_intent_factors(self, intent_data: Dict[str, Any], 
                              escalation_factors: List[str]) -> float:
        """分析意图因素对升级的影响"""
        if intent_data.get("intent") in self.escalation_rules["intent_escalation"]:
            escalation_factors.append("Complex customer intent requiring human attention")
            
            # 考虑意图识别置信度
            confidence = intent_data.get("confidence", 0.5)
            return 0.3 * confidence
        
        return 0.0
    
    def _analyze_complexity_factors(self, context_data: Dict[str, Any], 
                                  escalation_factors: List[str]) -> float:
        """分析对话复杂度因素"""
        conversation_complexity = context_data.get("conversation_complexity", 0)
        
        if conversation_complexity > 10:
            escalation_factors.append("Long conversation requiring human review")
            
            # 复杂度逐渐增加升级权重
            complexity_score = min(0.3, (conversation_complexity - 10) * 0.02)
            return complexity_score
        
        return 0.0
    
    def _analyze_agent_quality_factors(self, agent_responses: Dict[str, Any], 
                                     escalation_factors: List[str]) -> float:
        """分析代理响应质量因素"""
        if not agent_responses:
            return 0.0
        
        error_agents = [agent_id for agent_id, response in agent_responses.items() 
                      if response.get("error") or response.get("fallback")]
        
        if len(error_agents) > 1:
            escalation_factors.append("Multiple agent failures detected")
            
            # 多个代理失败时增加升级权重
            error_ratio = len(error_agents) / len(agent_responses)
            return 0.3 * min(1.0, error_ratio * 2)
        
        return 0.0
    
    def _calculate_escalation_confidence(self, context_data: Dict[str, Any]) -> float:
        """
        计算升级建议置信度
        
        参数:
            context_data: 上下文数据
            
        返回:
            float: 置信度分数
        """
        confidence = 0.5  # 基础置信度
        
        # 数据完整度影响置信度
        if context_data.get("sentiment"):
            confidence += 0.1
        if context_data.get("intent"):
            confidence += 0.1
        if context_data.get("compliance"):
            confidence += 0.1
        if context_data.get("agent_responses"):
            confidence += 0.2
        
        return min(1.0, confidence)
    
    def _get_fallback_escalation_result(self, error_msg: str) -> Dict[str, Any]:
        """获取错误情况下的保守升级结果"""
        return {
            "escalation_recommended": True,
            "escalation_score": 1.0,
            "escalation_factors": ["Error in escalation analysis - defaulting to human review"],
            "confidence": 0.5,
            "error": error_msg,
            "fallback": True
        }
    
    def update_escalation_rules(self, new_rules: Dict[str, Any]) -> None:
        """
        更新升级规则配置
        
        参数:
            new_rules: 新的规则配置
        """
        try:
            self.escalation_rules.update(new_rules)
            self.logger.info(f"升级规则已更新: {new_rules}")
        except Exception as e:
            self.logger.error(f"更新升级规则失败: {e}")
    
    def get_escalation_rules(self) -> Dict[str, Any]:
        """获取当前升级规则配置"""
        return self.escalation_rules.copy()