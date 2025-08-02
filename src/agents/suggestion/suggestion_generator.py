"""
建议生成器 - 重构版

生成各类智能建议和优化方案的主要协调器。
整合模板管理、性能建议和优化分析功能。
"""

from typing import Dict, Any, List
from src.utils import get_logger

from .suggestion_templates import SuggestionTemplateManager  
from .performance_suggestions import PerformanceSuggestionGenerator
from .optimization_analyzer import OptimizationAnalyzer


class SuggestionGenerator:
    """
    建议生成器 - 重构版
    
    协调各种建议生成组件，提供统一的建议生成接口。
    整合模板匹配、性能分析和优化识别功能。
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.logger = get_logger(f"suggestion_generator_{tenant_id}")
        
        # 初始化子组件
        self.template_manager = SuggestionTemplateManager(tenant_id)
        self.performance_generator = PerformanceSuggestionGenerator(tenant_id)
        self.optimization_analyzer = OptimizationAnalyzer(tenant_id)
        
        self.logger.info(f"建议生成器初始化完成: tenant_id={tenant_id}")
    
    async def generate_improvement_suggestions(self, context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        生成系统改进建议
        
        参数:
            context_data: 上下文数据
            
        返回:
            List[Dict[str, Any]]: 改进建议列表
        """
        suggestions = []
        
        try:
            # 基于性能数据生成建议
            performance_suggestions = self.performance_generator.generate_performance_suggestions(context_data)
            suggestions.extend(performance_suggestions)
            
            # 基于模板生成用户体验建议
            ux_templates = self.template_manager.get_matching_templates("user_experience", context_data)
            for template in ux_templates:
                suggestions.append(self._template_to_suggestion(template, "improvement"))
            
            # 基于错误数据生成建议
            error_suggestions = self._generate_error_based_suggestions(context_data)
            suggestions.extend(error_suggestions)
            
            # 应用优先级排序
            return self._prioritize_suggestions(suggestions)
            
        except Exception as e:
            self.logger.error(f"生成改进建议失败: {e}")
            return []
    
    async def analyze_optimization_opportunities(self, context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        分析优化机会
        
        参数:
            context_data: 上下文数据
            
        返回:
            List[Dict[str, Any]]: 优化机会列表
        """
        try:
            # 使用优化分析器进行分析
            return self.optimization_analyzer.analyze_optimization_opportunities(context_data)
            
        except Exception as e:
            self.logger.error(f"分析优化机会失败: {e}")
            return []
    
    async def generate_general_suggestions(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成一般性建议
        
        参数:
            context_data: 上下文数据
            
        返回:
            Dict[str, Any]: 一般性建议
        """
        try:
            # 评估系统健康状况
            system_health = self._assess_system_health(context_data)
            
            suggestions = []
            
            # 根据系统状态生成相应建议
            suggestions = self._get_status_suggestions(system_health["overall_status"])
            
            return {
                "suggestions": suggestions,
                "escalation_recommended": system_health["overall_status"] == "critical",
                "system_health": system_health,
                "general_advice": self._get_general_advice(system_health)
            }
            
        except Exception as e:
            self.logger.error(f"生成一般性建议失败: {e}")
            return {
                "suggestions": [],
                "escalation_recommended": False,
                "general_advice": "System operating normally"
            }
    
    def _template_to_suggestion(self, template: Dict[str, Any], suggestion_type: str) -> Dict[str, Any]:
        """
        将模板转换为建议格式
        
        参数:
            template: 建议模板
            suggestion_type: 建议类型
            
        返回:
            Dict[str, Any]: 格式化的建议
        """
        return {
            "type": suggestion_type,
            "title": template.get("title", "System improvement"),
            "description": template.get("description", ""),
            "category": template.get("category", "general"),
            "priority": self._map_impact_to_priority(template.get("impact", "medium")),
            "effort": template.get("effort", "medium"),
            "impact": template.get("impact", "medium")
        }
    
    def _map_impact_to_priority(self, impact: str) -> str:
        """
        将影响程度映射到优先级
        
        参数:
            impact: 影响程度
            
        返回:
            str: 优先级
        """
        mapping = {
            "high": "high",
            "medium": "medium", 
            "low": "low"
        }
        return mapping.get(impact, "medium")
    
    def _generate_error_based_suggestions(self, context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        基于错误模式生成建议
        
        参数:
            context_data: 上下文数据
            
        返回:
            List[Dict[str, Any]]: 错误相关建议
        """
        suggestions = []
        
        try:
            # 分析错误率
            agent_responses = context_data.get("agent_responses", {})
            error_count = len([resp for resp in agent_responses.values() if resp.get("error")])
            
            if error_count > 1:
                suggestions.append({
                    "type": "reliability",
                    "priority": "high",
                    "title": "Multiple agent errors detected",
                    "suggestion": f"Multiple agent errors detected ({error_count}). Review error handling and monitoring.",
                    "impact": "Improved system reliability",
                    "effort": "medium"
                })
            
            # 分析个性化程度
            customer_profile = context_data.get("customer_profile", {})
            if not customer_profile:
                suggestions.append({
                    "type": "user_experience",
                    "priority": "medium",
                    "title": "Customer profiling opportunity",
                    "suggestion": "Implement customer profiling to provide personalized experiences.",
                    "impact": "Enhanced customer satisfaction and engagement",
                    "effort": "medium"
                })
                
        except Exception as e:
            self.logger.error(f"生成错误建议失败: {e}")
            
        return suggestions
    
    def _assess_system_health(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """评估系统健康状况"""
        health_score = 1.0
        issues = []
        
        # 检查错误率
        agent_responses = context_data.get("agent_responses", {})
        if agent_responses:
            error_rate = len([r for r in agent_responses.values() if r.get("error")]) / len(agent_responses)
            if error_rate > 0.3:
                health_score -= 0.4
                issues.append("High error rate detected")
            elif error_rate > 0.1:
                health_score -= 0.2
                issues.append("Elevated error rate")
        
        # 检查响应时间
        response_time = context_data.get("average_response_time", 0)
        if response_time > 2000:
            health_score -= 0.3
            issues.append("Slow response time")
        elif response_time > 1000:
            health_score -= 0.1
            issues.append("Moderate response time")
        
        # 确定整体状态
        status_map = [(0.8, "good"), (0.6, "warning"), (0.4, "critical")]
        status = "severe"
        for threshold, status_name in status_map:
            if health_score >= threshold:
                status = status_name
                break
        
        return {
            "overall_status": status,
            "health_score": max(0.0, health_score),
            "issues": issues
        }
    
    def _get_status_suggestions(self, status: str) -> List[Dict[str, Any]]:
        """根据状态获取建议"""
        suggestions_map = {
            "good": [{"type": "system_enhancement", "priority": "low", "title": "Implement conversation analytics", 
                     "suggestion": "Consider implementing conversation analytics dashboard", "impact": "Better visibility", "effort": "medium"}],
            "warning": [{"type": "maintenance", "priority": "medium", "title": "System maintenance recommended", 
                        "suggestion": "Schedule system maintenance to address performance issues", "impact": "Improved stability", "effort": "low"}],
            "critical": [{"type": "critical", "priority": "critical", "title": "Immediate attention required", 
                         "suggestion": "System showing critical issues requiring immediate investigation", "impact": "Prevent failure", "effort": "high"}],
            "severe": [{"type": "warning", "priority": "medium", "title": "System monitoring recommended", 
                       "suggestion": "Increased monitoring recommended due to system warnings", "impact": "Early detection", "effort": "low"}]
        }
        return suggestions_map.get(status, [])
    
    def _get_general_advice(self, system_health: Dict[str, Any]) -> str:
        """基于系统健康状况获取一般性建议"""
        advice_map = {
            "good": "System is operating within normal parameters. Continue monitoring.",
            "warning": "System showing some performance issues. Consider optimization.",
            "critical": "System requires immediate attention to prevent failures.",
            "severe": "System in critical state. Immediate intervention required."
        }
        return advice_map.get(system_health["overall_status"], "System status unclear. Manual review recommended.")
    
    def _prioritize_suggestions(self, suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """对建议按优先级排序"""
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        
        return sorted(suggestions, key=lambda x: priority_order.get(x.get("priority", "low"), 3))
    
    def add_suggestion_template(self, category: str, template: Dict[str, Any]) -> None:
        """
        添加自定义建议模板
        
        参数:
            category: 建议类别
            template: 建议模板
        """
        self.template_manager.add_custom_template(category, template)
    
    def get_suggestion_categories(self) -> List[str]:
        """获取所有建议类别"""
        return self.template_manager.get_all_categories()
    
    def get_generator_info(self) -> Dict[str, Any]:
        """获取生成器信息"""
        return {
            "tenant_id": self.tenant_id,
            "components": {
                "template_manager": self.template_manager.get_manager_info(),
                "performance_generator": self.performance_generator.get_generator_info(),
                "optimization_analyzer": self.optimization_analyzer.get_analyzer_info()
            },
            "suggestion_categories": self.get_suggestion_categories()
        }