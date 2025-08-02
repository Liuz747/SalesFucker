"""
性能建议生成器

专门处理性能相关的建议生成和优化分析。
分析系统性能指标并提供针对性的改进建议。
"""

from typing import Dict, Any, List
from src.utils import get_logger


class PerformanceSuggestionGenerator:
    """
    性能建议生成器
    
    基于性能指标生成针对性的优化建议。
    涵盖响应时间、资源使用、错误率等方面。
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.logger = get_logger(f"performance_suggestions_{tenant_id}")
        
        # 性能阈值配置
        self.performance_thresholds = {
            "response_time_ms": {"good": 500, "warning": 1000, "critical": 2000},
            "error_rate": {"good": 0.01, "warning": 0.05, "critical": 0.1},
            "memory_usage_percent": {"good": 70, "warning": 85, "critical": 95},
            "cpu_usage_percent": {"good": 70, "warning": 85, "critical": 95},
            "agent_count": {"good": 5, "warning": 8, "critical": 10}
        }
        
        self.logger.info(f"性能建议生成器初始化完成: tenant_id={tenant_id}")
    
    def generate_performance_suggestions(self, context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        生成性能相关建议
        
        参数:
            context_data: 上下文数据，包含性能指标
            
        返回:
            List[Dict[str, Any]]: 性能建议列表
        """
        suggestions = []
        
        # 分析响应时间
        response_time_suggestions = self._analyze_response_time(context_data)
        suggestions.extend(response_time_suggestions)
        
        # 分析错误率
        error_rate_suggestions = self._analyze_error_rate(context_data)
        suggestions.extend(error_rate_suggestions)
        
        # 分析资源使用
        resource_suggestions = self._analyze_resource_usage(context_data)
        suggestions.extend(resource_suggestions)
        
        # 分析代理效率
        agent_efficiency_suggestions = self._analyze_agent_efficiency(context_data)
        suggestions.extend(agent_efficiency_suggestions)
        
        return self._prioritize_suggestions(suggestions)
    
    def _analyze_response_time(self, context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """分析响应时间并生成建议"""
        suggestions = []
        response_time = context_data.get("average_response_time", 0)
        
        thresholds = self.performance_thresholds["response_time_ms"]
        
        if response_time > thresholds["critical"]:
            suggestions.append({
                "type": "performance",
                "priority": "critical",
                "title": "Critical response time issue",
                "suggestion": f"Response time ({response_time}ms) exceeds critical threshold. Immediate optimization needed.",
                "impact": "System performance severely degraded",
                "actions": [
                    "Review and optimize slow database queries",
                    "Implement response caching for frequently accessed data",
                    "Consider horizontal scaling of processing components",
                    "Analyze and optimize agent workflow efficiency"
                ],
                "effort": "high"
            })
        elif response_time > thresholds["warning"]:
            suggestions.append({
                "type": "performance", 
                "priority": "high",
                "title": "Response time optimization needed",
                "suggestion": f"Response time ({response_time}ms) above recommended threshold. Performance tuning recommended.",
                "impact": "Improved user experience and system efficiency",
                "actions": [
                    "Enable query result caching",
                    "Optimize frequent database operations",
                    "Review agent processing sequences",
                    "Consider asynchronous processing for non-critical operations"
                ],
                "effort": "medium"
            })
        elif response_time > thresholds["good"]:
            suggestions.append({
                "type": "performance",
                "priority": "medium", 
                "title": "Response time improvement opportunity",
                "suggestion": f"Response time ({response_time}ms) can be optimized for better performance.",
                "impact": "Enhanced responsiveness and user satisfaction",
                "actions": [
                    "Implement selective caching strategies",
                    "Review and tune frequently used queries",
                    "Consider connection pooling optimizations"
                ],
                "effort": "low"
            })
        
        return suggestions
    
    def _analyze_error_rate(self, context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """分析错误率并生成建议"""
        suggestions = []
        
        # 计算整体错误率
        total_requests = context_data.get("total_requests", 0)
        error_requests = context_data.get("error_requests", 0)
        
        if total_requests > 0:
            error_rate = error_requests / total_requests
            thresholds = self.performance_thresholds["error_rate"]
            
            if error_rate > thresholds["critical"]:
                suggestions.append({
                    "type": "reliability",
                    "priority": "critical",
                    "title": "Critical error rate detected",
                    "suggestion": f"Error rate ({error_rate:.2%}) is critically high. Immediate investigation required.",
                    "impact": "System reliability compromised",
                    "actions": [
                        "Investigate and fix root causes of errors",
                        "Implement circuit breaker patterns",
                        "Add comprehensive error monitoring",
                        "Review agent failure recovery mechanisms"
                    ],
                    "effort": "high"
                })
            elif error_rate > thresholds["warning"]:
                suggestions.append({
                    "type": "reliability",
                    "priority": "high", 
                    "title": "Elevated error rate needs attention",
                    "suggestion": f"Error rate ({error_rate:.2%}) is above normal levels. System reliability review recommended.",
                    "impact": "Improved system stability and user experience",
                    "actions": [
                        "Analyze error patterns and common failure points",
                        "Implement better error handling and recovery",
                        "Add proactive monitoring and alerting",
                        "Review agent timeout and retry mechanisms"
                    ],
                    "effort": "medium"
                })
        
        # 分析特定代理错误
        agent_responses = context_data.get("agent_responses", {})
        failed_agents = [agent_id for agent_id, response in agent_responses.items() 
                        if response.get("error") or response.get("fallback")]
        
        if len(failed_agents) > 2:
            suggestions.append({
                "type": "reliability",
                "priority": "high",
                "title": "Multiple agent failures detected", 
                "suggestion": f"{len(failed_agents)} agents reported failures or fallbacks. System reliability compromised.",
                "impact": "Improved conversation success rate",
                "actions": [
                    "Investigate failed agents for common issues",
                    "Review agent dependencies and integration points",
                    "Implement better fallback mechanisms",
                    "Add agent-specific health monitoring"
                ],
                "effort": "medium"
            })
        
        return suggestions
    
    def _analyze_resource_usage(self, context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """分析资源使用情况并生成建议"""
        suggestions = []
        
        # 分析内存使用
        memory_usage = context_data.get("memory_usage_percent", 0)
        memory_thresholds = self.performance_thresholds["memory_usage_percent"]
        
        if memory_usage > memory_thresholds["critical"]:
            suggestions.append({
                "type": "resource_optimization",
                "priority": "critical",
                "title": "Critical memory usage detected",
                "suggestion": f"Memory usage ({memory_usage}%) is critically high. Immediate action required.",
                "impact": "Prevent system instability and crashes",
                "actions": [
                    "Investigate memory leaks in agent processes",
                    "Implement memory usage monitoring and alerts",
                    "Optimize data structures and caching strategies",
                    "Consider increasing available memory resources"
                ],
                "effort": "high"
            })
        elif memory_usage > memory_thresholds["warning"]:
            suggestions.append({
                "type": "resource_optimization",
                "priority": "medium",
                "title": "Memory optimization recommended",
                "suggestion": f"Memory usage ({memory_usage}%) approaching limits. Optimization recommended.",
                "impact": "Improved system stability and performance",
                "actions": [
                    "Review and optimize memory-intensive operations",
                    "Implement memory usage monitoring",
                    "Consider memory-efficient data structures",
                    "Optimize caching strategies"
                ],
                "effort": "medium"
            })
        
        # 分析CPU使用
        cpu_usage = context_data.get("cpu_usage_percent", 0)
        cpu_thresholds = self.performance_thresholds["cpu_usage_percent"]
        
        if cpu_usage > cpu_thresholds["warning"]:
            suggestions.append({
                "type": "resource_optimization",
                "priority": "medium",
                "title": "CPU optimization opportunity",
                "suggestion": f"CPU usage ({cpu_usage}%) indicates optimization opportunities exist.",
                "impact": "Better resource utilization and responsiveness",
                "actions": [
                    "Profile CPU-intensive operations",
                    "Consider asynchronous processing for I/O bound tasks",
                    "Optimize algorithmic complexity where possible",
                    "Implement CPU usage monitoring"
                ],
                "effort": "medium"
            })
        
        return suggestions
    
    def _analyze_agent_efficiency(self, context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """分析代理效率并生成建议"""
        suggestions = []
        
        # 分析活跃代理数量
        active_agents = context_data.get("active_agents", [])
        agent_count = len(active_agents) if isinstance(active_agents, list) else active_agents
        
        agent_thresholds = self.performance_thresholds["agent_count"]
        
        if agent_count > agent_thresholds["critical"]:
            suggestions.append({
                "type": "workflow_optimization",
                "priority": "medium",
                "title": "Too many agents involved in processing",
                "suggestion": f"Large number of agents ({agent_count}) may indicate workflow inefficiency.",
                "impact": "Streamlined processing and reduced complexity",
                "actions": [
                    "Review agent workflow and eliminate unnecessary steps",
                    "Consider consolidating similar agent functions",
                    "Implement parallel processing where appropriate",
                    "Optimize agent coordination mechanisms"
                ],
                "effort": "medium"
            })
        
        # 分析代理响应时间分布
        agent_responses = context_data.get("agent_responses", {})
        slow_agents = []
        
        for agent_id, response in agent_responses.items():
            processing_time = response.get("processing_time_ms", 0)
            if processing_time > 1000:  # 超过1秒
                slow_agents.append((agent_id, processing_time))
        
        if slow_agents:
            suggestions.append({
                "type": "agent_optimization",
                "priority": "medium",
                "title": "Slow agent performance detected",
                "suggestion": f"{len(slow_agents)} agents showing slow response times. Individual optimization needed.",
                "impact": "Improved overall system response time",
                "actions": [
                    "Profile slow agents for performance bottlenecks",
                    "Optimize agent-specific processing logic",
                    "Review agent resource allocation",
                    "Consider agent-specific caching strategies"
                ],
                "effort": "medium",
                "details": {"slow_agents": slow_agents}
            })
        
        return suggestions
    
    def _prioritize_suggestions(self, suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """对建议按优先级排序"""
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        
        return sorted(suggestions, key=lambda x: priority_order.get(x.get("priority", "low"), 3))
    
    def update_performance_thresholds(self, new_thresholds: Dict[str, Any]) -> None:
        """
        更新性能阈值配置
        
        参数:
            new_thresholds: 新的阈值配置
        """
        try:
            for metric, thresholds in new_thresholds.items():
                if metric in self.performance_thresholds:
                    self.performance_thresholds[metric].update(thresholds)
                else:
                    self.performance_thresholds[metric] = thresholds
            
            self.logger.info(f"性能阈值更新完成: {list(new_thresholds.keys())}")
            
        except Exception as e:
            self.logger.error(f"性能阈值更新失败: {e}")
            raise
    
    def get_performance_thresholds(self) -> Dict[str, Any]:
        """获取当前性能阈值配置"""
        return self.performance_thresholds.copy()
    
    def get_generator_info(self) -> Dict[str, Any]:
        """获取生成器信息"""
        return {
            "tenant_id": self.tenant_id,
            "monitored_metrics": list(self.performance_thresholds.keys()),
            "threshold_levels": ["good", "warning", "critical"]
        }