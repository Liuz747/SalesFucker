"""
建议模板管理器

管理各类建议模板和模板匹配逻辑。
提供模板CRUD操作和智能匹配功能。
"""

from typing import Dict, Any, List
from utils import get_component_logger


class SuggestionTemplateManager:
    """
    建议模板管理器
    
    管理系统内置和动态添加的建议模板。
    支持基于上下文的智能模板匹配。
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.logger = get_component_logger(f"suggestion_templates_{tenant_id}")
        
        # 建议类型配置
        self.suggestion_types = {
            "escalation": "Recommend human intervention",
            "improvement": "System enhancement suggestion",
            "strategy": "Alternative approach recommendation",
            "optimization": "Performance optimization suggestion",
            "user_experience": "User experience improvement",
            "automation": "Process automation opportunity"
        }
        
        # 内置建议模板库
        self.builtin_templates = {
            "performance": [
                {
                    "title": "Implement response caching",
                    "description": "Cache common query responses to reduce processing time",
                    "category": "performance_optimization",
                    "effort": "medium",
                    "impact": "high",
                    "trigger_conditions": {"response_time_ms": {"gt": 1000}}
                },
                {
                    "title": "Optimize database queries",
                    "description": "Review and optimize frequently used database queries",
                    "category": "performance_optimization", 
                    "effort": "low",
                    "impact": "medium",
                    "trigger_conditions": {"database_query_count": {"gt": 5}}
                },
                {
                    "title": "Enable response compression",
                    "description": "Compress API responses to reduce bandwidth usage",
                    "category": "performance_optimization",
                    "effort": "low",
                    "impact": "low",
                    "trigger_conditions": {"response_size_kb": {"gt": 100}}
                }
            ],
            "user_experience": [
                {
                    "title": "Personalized greeting messages",
                    "description": "Implement dynamic greeting based on customer history",
                    "category": "user_experience",
                    "effort": "low",
                    "impact": "medium",
                    "trigger_conditions": {"customer_visits": {"gt": 1}}
                },
                {
                    "title": "Proactive assistance",
                    "description": "Offer help based on customer browsing patterns",
                    "category": "user_experience",
                    "effort": "high",
                    "impact": "high",
                    "trigger_conditions": {"session_duration_min": {"gt": 5}}
                },
                {
                    "title": "Multi-language support",
                    "description": "Add support for additional customer languages",
                    "category": "user_experience",
                    "effort": "high",
                    "impact": "high",
                    "trigger_conditions": {"non_default_language_requests": {"gt": 10}}
                }
            ],
            "automation": [
                {
                    "title": "Automated FAQ responses",
                    "description": "Implement intelligent FAQ matching for common questions",
                    "category": "automation",
                    "effort": "medium",
                    "impact": "medium",
                    "trigger_conditions": {"repeated_questions": {"gt": 3}}
                },
                {
                    "title": "Smart routing to specialists",
                    "description": "Automatically route complex queries to human specialists",
                    "category": "automation",
                    "effort": "medium",
                    "impact": "high",
                    "trigger_conditions": {"escalation_rate": {"gt": 0.3}}
                }
            ],
            "reliability": [
                {
                    "title": "Implement circuit breaker",
                    "description": "Add circuit breaker pattern for external service calls",
                    "category": "reliability",
                    "effort": "medium",
                    "impact": "high",
                    "trigger_conditions": {"service_error_rate": {"gt": 0.1}}
                },
                {
                    "title": "Add health monitoring",
                    "description": "Implement comprehensive health checks for all components",
                    "category": "reliability",
                    "effort": "low",
                    "impact": "medium",
                    "trigger_conditions": {"component_failures": {"gt": 0}}
                }
            ]
        }
        
        # 动态添加的模板
        self.custom_templates = {}
        
        self.logger.info(f"建议模板管理器初始化完成: tenant_id={tenant_id}")
    
    def get_matching_templates(self, category: str, context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        获取匹配的建议模板
        
        参数:
            category: 建议类别
            context_data: 上下文数据
            
        返回:
            List[Dict[str, Any]]: 匹配的模板列表
        """
        matching_templates = []
        
        # 检查内置模板
        builtin_category_templates = self.builtin_templates.get(category, [])
        for template in builtin_category_templates:
            if self._template_matches_context(template, context_data):
                matching_templates.append(template.copy())
        
        # 检查自定义模板
        custom_category_templates = self.custom_templates.get(category, [])
        for template in custom_category_templates:
            if self._template_matches_context(template, context_data):
                matching_templates.append(template.copy())
        
        return matching_templates
    
    def _template_matches_context(self, template: Dict[str, Any], 
                                context_data: Dict[str, Any]) -> bool:
        """
        检查模板是否匹配上下文条件
        
        参数:
            template: 建议模板
            context_data: 上下文数据
            
        返回:
            bool: 是否匹配
        """
        trigger_conditions = template.get("trigger_conditions", {})
        
        if not trigger_conditions:
            return True  # 没有触发条件，默认匹配
        
        for condition_key, condition_value in trigger_conditions.items():
            context_value = context_data.get(condition_key)
            
            if context_value is None:
                continue  # 上下文中没有这个值，跳过这个条件
            
            # 支持不同类型的条件比较
            if isinstance(condition_value, dict):
                if "gt" in condition_value and context_value <= condition_value["gt"]:
                    return False
                if "lt" in condition_value and context_value >= condition_value["lt"]:
                    return False
                if "eq" in condition_value and context_value != condition_value["eq"]:
                    return False
            else:
                if context_value != condition_value:
                    return False
        
        return True
    
    def add_custom_template(self, category: str, template: Dict[str, Any]) -> None:
        """
        添加自定义建议模板
        
        参数:
            category: 建议类别
            template: 建议模板
        """
        try:
            if category not in self.custom_templates:
                self.custom_templates[category] = []
            
            # 验证模板格式
            required_fields = ["title", "description", "effort", "impact"]
            for field in required_fields:
                if field not in template:
                    raise ValueError(f"模板缺少必需字段: {field}")
            
            self.custom_templates[category].append(template)
            self.logger.info(f"添加自定义模板: {category} - {template['title']}")
            
        except Exception as e:
            self.logger.error(f"添加自定义模板失败: {e}")
            raise
    
    def remove_custom_template(self, category: str, template_title: str) -> bool:
        """
        移除自定义建议模板
        
        参数:
            category: 建议类别
            template_title: 模板标题
            
        返回:
            bool: 是否成功移除
        """
        try:
            if category not in self.custom_templates:
                return False
            
            original_count = len(self.custom_templates[category])
            self.custom_templates[category] = [
                t for t in self.custom_templates[category] 
                if t.get("title") != template_title
            ]
            
            removed = len(self.custom_templates[category]) < original_count
            if removed:
                self.logger.info(f"移除自定义模板: {category} - {template_title}")
            
            return removed
            
        except Exception as e:
            self.logger.error(f"移除自定义模板失败: {e}")
            return False
    
    def get_all_categories(self) -> List[str]:
        """获取所有可用的建议类别"""
        categories = set(self.builtin_templates.keys())
        categories.update(self.custom_templates.keys())
        return list(categories)
    
    def get_template_count(self, category: str = None) -> Dict[str, int]:
        """
        获取模板统计信息
        
        参数:
            category: 可选的特定类别
            
        返回:
            Dict[str, int]: 模板统计
        """
        if category:
            builtin_count = len(self.builtin_templates.get(category, []))
            custom_count = len(self.custom_templates.get(category, []))
            return {
                "builtin": builtin_count,
                "custom": custom_count,
                "total": builtin_count + custom_count
            }
        
        # 全部类别统计
        stats = {"builtin": 0, "custom": 0, "total": 0}
        
        for templates in self.builtin_templates.values():
            stats["builtin"] += len(templates)
        
        for templates in self.custom_templates.values():
            stats["custom"] += len(templates)
        
        stats["total"] = stats["builtin"] + stats["custom"]
        return stats
    
    def get_suggestion_types(self) -> Dict[str, str]:
        """获取建议类型配置"""
        return self.suggestion_types.copy()
    
    def get_manager_info(self) -> Dict[str, Any]:
        """获取模板管理器信息"""
        return {
            "tenant_id": self.tenant_id,
            "available_categories": self.get_all_categories(),
            "template_counts": self.get_template_count(),
            "suggestion_types": list(self.suggestion_types.keys())
        }