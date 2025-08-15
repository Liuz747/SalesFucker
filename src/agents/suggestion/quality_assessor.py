"""
质量评估器

负责对话质量分析和改进建议生成。
提供系统性能评估和优化建议。
"""

from typing import Dict, Any, List
import logging
from ..base import ThreadState
from src.utils import get_component_logger


class QualityAssessor:
    """
    质量评估器
    
    分析对话质量、系统性能，并生成改进建议。
    提供系统优化和用户体验提升的建议。
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.logger = get_component_logger(f"quality_assessor_{tenant_id}")
        
        # 质量评估配置
        self.quality_thresholds = {
            "min_quality_score": 0.6,
            "max_agents_involved": 6,
            "max_error_rate": 0.2,
            "min_response_confidence": 0.7
        }
        
        # 改进建议类型
        self.improvement_categories = {
            "performance": "System performance optimization",
            "reliability": "System reliability improvement", 
            "personalization": "Customer experience personalization",
            "accuracy": "Response accuracy enhancement",
            "efficiency": "Workflow efficiency improvement"
        }
        
        self.logger.info(f"质量评估器初始化完成: tenant_id={tenant_id}")
    
    async def assess_conversation_quality(self, state: ThreadState) -> List[Dict[str, Any]]:
        """
        分析对话质量并提供改进建议
        
        参数:
            state: 对话状态
            
        返回:
            List[Dict[str, Any]]: 改进建议列表
        """
        suggestions = []
        
        # 分析响应效率
        efficiency_suggestions = self._assess_response_efficiency(state)
        suggestions.extend(efficiency_suggestions)
        
        # 分析系统可靠性
        reliability_suggestions = self._assess_system_reliability(state)
        suggestions.extend(reliability_suggestions)
        
        # 分析个性化程度
        personalization_suggestions = self._assess_personalization_level(state)
        suggestions.extend(personalization_suggestions)
        
        # 分析准确性
        accuracy_suggestions = self._assess_response_accuracy(state)
        suggestions.extend(accuracy_suggestions)
        
        # 过滤和排序建议
        filtered_suggestions = self._filter_and_prioritize_suggestions(suggestions)
        
        self.logger.info(f"生成了 {len(filtered_suggestions)} 条质量改进建议")
        return filtered_suggestions
    
    def _assess_response_efficiency(self, state: ThreadState) -> List[Dict[str, Any]]:
        """评估响应效率"""
        suggestions = []
        
        # 检查涉及的代理数量
        if len(state.active_agents) > self.quality_thresholds["max_agents_involved"]:
            suggestions.append({
                "type": "performance",
                "priority": "medium",
                "suggestion": "Consider optimizing agent workflow - many agents involved",
                "impact": "Improve response time",
                "metric": f"Active agents: {len(state.active_agents)}",
                "target": f"Target: ≤{self.quality_thresholds['max_agents_involved']} agents"
            })
        
        # 检查处理完成度
        if not state.processing_complete:
            suggestions.append({
                "type": "efficiency",
                "priority": "high",
                "suggestion": "Incomplete processing detected - review workflow completion logic",
                "impact": "Ensure all customer queries are fully addressed",
                "metric": "Processing incomplete",
                "target": "100% processing completion"
            })
        
        return suggestions
    
    def _assess_system_reliability(self, state: ThreadState) -> List[Dict[str, Any]]:
        """评估系统可靠性"""
        suggestions = []
        
        # 计算错误率
        total_responses = len(state.agent_responses)
        error_responses = [resp for resp in state.agent_responses.values() 
                         if resp.get("error") or resp.get("fallback")]
        
        if total_responses > 0:
            error_rate = len(error_responses) / total_responses
            
            if error_rate > self.quality_thresholds["max_error_rate"]:
                suggestions.append({
                    "type": "reliability",
                    "priority": "high",
                    "suggestion": "Multiple agent failures detected - investigate system reliability",
                    "impact": "Improve conversation success rate",
                    "metric": f"Error rate: {error_rate:.2%}",
                    "target": f"Target: ≤{self.quality_thresholds['max_error_rate']:.0%}",
                    "affected_agents": [agent_id for agent_id, resp in state.agent_responses.items() 
                                      if resp.get("error") or resp.get("fallback")]
                })
        
        return suggestions
    
    def _assess_personalization_level(self, state: ThreadState) -> List[Dict[str, Any]]:
        """评估个性化程度"""
        suggestions = []
        
        # 检查客户档案完整性
        if not state.customer_profile:
            suggestions.append({
                "type": "personalization",
                "priority": "medium",
                "suggestion": "Gather more customer profile data for better personalization",
                "impact": "Enhance customer experience",
                "metric": "No customer profile",
                "target": "Complete customer profile"
            })
        elif isinstance(state.customer_profile, dict) and len(state.customer_profile) < 3:
            suggestions.append({
                "type": "personalization",
                "priority": "low",
                "suggestion": "Expand customer profile data collection",
                "impact": "Improve personalized recommendations",
                "metric": f"Profile fields: {len(state.customer_profile)}",
                "target": "≥5 profile fields"
            })
        
        return suggestions
    
    def _assess_response_accuracy(self, state: ThreadState) -> List[Dict[str, Any]]:
        """评估响应准确性"""
        suggestions = []
        
        # 检查置信度水平
        low_confidence_agents = []
        for agent_id, response in state.agent_responses.items():
            confidence = response.get("confidence", 1.0)
            if confidence < self.quality_thresholds["min_response_confidence"]:
                low_confidence_agents.append(agent_id)
        
        if low_confidence_agents:
            suggestions.append({
                "type": "accuracy",
                "priority": "medium",
                "suggestion": "Some agents reported low confidence - review training data or models",
                "impact": "Improve response accuracy and reliability",
                "metric": f"Low confidence agents: {len(low_confidence_agents)}",
                "target": f"Confidence ≥{self.quality_thresholds['min_response_confidence']}",
                "affected_agents": low_confidence_agents
            })
        
        return suggestions
    
    def _filter_and_prioritize_suggestions(self, suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """过滤和排序建议"""
        if not suggestions:
            return suggestions
        
        # 按优先级排序
        priority_order = {"high": 3, "medium": 2, "low": 1}
        suggestions.sort(
            key=lambda x: priority_order.get(x.get("priority", "low"), 1),
            reverse=True
        )
        
        # 限制建议数量
        max_suggestions = 10
        return suggestions[:max_suggestions]
    
    def calculate_conversation_quality_score(self, state: ThreadState) -> float:
        """
        计算对话质量分数
        
        参数:
            state: 对话状态
            
        返回:
            float: 质量分数 (0.0-1.0)
        """
        score = 0.5  # 基础分数
        
        # 完成度评分 (20%)
        if state.processing_complete:
            score += 0.2
        
        # 错误率评分 (30%)
        total_responses = len(state.agent_responses)
        if total_responses > 0:
            error_responses = len([resp for resp in state.agent_responses.values() 
                                 if resp.get("error") or resp.get("fallback")])
            error_rate = error_responses / total_responses
            score += 0.3 * (1 - error_rate)
        
        # 个性化评分 (20%)
        if state.customer_profile and len(state.customer_profile) > 2:
            profile_completeness = min(1.0, len(state.customer_profile) / 5)
            score += 0.2 * profile_completeness
        
        # 效率评分 (20%)
        if len(state.active_agents) <= self.quality_thresholds["max_agents_involved"]:
            score += 0.2
        else:
            # 超出理想代理数量时降分
            excess_ratio = (len(state.active_agents) - self.quality_thresholds["max_agents_involved"]) / 5
            score += 0.2 * max(0, 1 - excess_ratio)
        
        # 一致性评分 (10%)
        if not any(resp.get("fallback") for resp in state.agent_responses.values()):
            score += 0.1
        
        return min(1.0, max(0.0, score))
    
    def generate_system_performance_suggestions(self, performance_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        生成系统性能改进建议
        
        参数:
            performance_data: 系统性能数据
            
        返回:
            List[Dict[str, Any]]: 性能改进建议
        """
        suggestions = []
        
        # 响应时间分析
        avg_response_time = performance_data.get("average_response_time", 0)
        if avg_response_time > 2000:  # 超过2秒
            suggestions.append({
                "type": "performance",
                "priority": "high",
                "suggestion": "Response time exceeds target - implement caching or optimize queries",
                "impact": "Significantly improve user experience",
                "metric": f"Avg response time: {avg_response_time}ms",
                "target": "Target: <1000ms"
            })
        
        # 错误率分析
        error_rate = performance_data.get("error_rate", 0)
        if error_rate > 5:  # 超过5%
            suggestions.append({
                "type": "reliability",
                "priority": "high",
                "suggestion": "High error rate detected - review error handling and system stability",
                "impact": "Improve system reliability",
                "metric": f"Error rate: {error_rate}%",
                "target": "Target: <2%"
            })
        
        # 处理量分析
        messages_processed = performance_data.get("messages_processed", 0)
        if messages_processed > 1000:  # 高处理量
            suggestions.append({
                "type": "performance",
                "priority": "medium",
                "suggestion": "High message volume - consider implementing load balancing",
                "impact": "Maintain performance under high load",
                "metric": f"Messages processed: {messages_processed}",
                "target": "Implement auto-scaling"
            })
        
        return suggestions
    
    def update_quality_thresholds(self, new_thresholds: Dict[str, Any]) -> None:
        """
        更新质量阈值配置
        
        参数:
            new_thresholds: 新的阈值配置
        """
        try:
            self.quality_thresholds.update(new_thresholds)
            self.logger.info(f"质量阈值已更新: {new_thresholds}")
        except Exception as e:
            self.logger.error(f"更新质量阈值失败: {e}")
    
    def get_quality_metrics(self) -> Dict[str, Any]:
        """获取质量评估配置信息"""
        return {
            "quality_thresholds": self.quality_thresholds.copy(),
            "improvement_categories": list(self.improvement_categories.keys()),
            "tenant_id": self.tenant_id,
            "assessor_id": f"quality_assessor_{self.tenant_id}"
        }