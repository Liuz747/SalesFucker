"""
LLM分析器

使用大语言模型进行上下文分析和智能决策。
提供基于AI的升级建议和情况评估。
"""

from typing import Dict, Any
import json
import logging
from src.llm import get_llm_client
from src.utils import get_component_logger


class LLMAnalyzer:
    """
    LLM分析器
    
    使用大语言模型进行复杂的上下文分析。
    提供基于AI的升级建议和智能决策支持。
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.logger = get_component_logger(f"llm_analyzer_{tenant_id}")
        
        # LLM客户端
        self.llm_client = get_llm_client()
        
        # 分析配置
        self.analysis_config = {
            "temperature": 0.3,
            "max_tokens": 1000,
            "timeout": 30
        }
        
        self.logger.info(f"LLM分析器初始化完成: tenant_id={tenant_id}")
    
    async def analyze_escalation_context(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用LLM分析升级需求
        
        参数:
            context_data: 上下文数据
            
        返回:
            Dict[str, Any]: LLM分析结果
        """
        try:
            analysis_prompt = self._build_escalation_prompt(context_data)
            
            messages = [{"role": "user", "content": analysis_prompt}]
            response = await self.llm_client.chat_completion(
                messages, 
                temperature=self.analysis_config["temperature"]
            )
            
            # 解析LLM响应
            parsed_result = self._parse_llm_response(response)
            
            # 添加LLM特定信息
            parsed_result.update({
                "analysis_type": "llm_contextual",
                "model_used": "gpt-4",
                "prompt_version": "v1.0"
            })
            
            return parsed_result
            
        except Exception as e:
            self.logger.warning(f"LLM升级分析失败: {e}")
            return self._get_fallback_llm_result()
    
    async def analyze_conversation_quality(self, conversation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用LLM分析对话质量
        
        参数:
            conversation_data: 对话数据
            
        返回:
            Dict[str, Any]: 质量分析结果
        """
        try:
            quality_prompt = self._build_quality_prompt(conversation_data)
            
            messages = [{"role": "user", "content": quality_prompt}]
            response = await self.llm_client.chat_completion(
                messages,
                temperature=self.analysis_config["temperature"]
            )
            
            # 解析质量分析结果
            quality_result = self._parse_quality_response(response)
            
            return {
                "quality_score": quality_result.get("quality_score", 0.5),
                "improvement_areas": quality_result.get("improvement_areas", []),
                "strengths": quality_result.get("strengths", []),
                "recommendations": quality_result.get("recommendations", []),
                "analysis_confidence": quality_result.get("confidence", 0.7),
                "llm_analysis": True
            }
            
        except Exception as e:
            self.logger.warning(f"LLM质量分析失败: {e}")
            return self._get_fallback_quality_result()
    
    async def generate_improvement_suggestions(self, system_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用LLM生成系统改进建议
        
        参数:
            system_data: 系统性能数据
            
        返回:
            Dict[str, Any]: 改进建议
        """
        try:
            improvement_prompt = self._build_improvement_prompt(system_data)
            
            messages = [{"role": "user", "content": improvement_prompt}]
            response = await self.llm_client.chat_completion(
                messages,
                temperature=0.4  # 稍高的创造性
            )
            
            suggestions = self._parse_improvement_response(response)
            
            return {
                "suggestions": suggestions.get("suggestions", []),
                "priority_areas": suggestions.get("priority_areas", []),
                "implementation_complexity": suggestions.get("complexity", "medium"),
                "expected_impact": suggestions.get("impact", "medium"),
                "llm_generated": True
            }
            
        except Exception as e:
            self.logger.warning(f"LLM改进建议生成失败: {e}")
            return self._get_fallback_improvement_result()
    
    def _build_escalation_prompt(self, context_data: Dict[str, Any]) -> str:
        """构建升级分析提示词"""
        return f"""
Analyze this customer service interaction and determine if human escalation is needed.

Context Data:
- Sentiment: {context_data.get('sentiment', {})}
- Intent: {context_data.get('intent', {})}
- Compliance: {context_data.get('compliance', {})}
- Agent Responses: {len(context_data.get('agent_responses', {}))} agents involved
- Conversation Complexity: {context_data.get('conversation_complexity', 0)} exchanges

Consider factors like:
1. Customer frustration or negative sentiment
2. Complex technical issues
3. Compliance or safety concerns
4. Repeated AI failures
5. High-value customer needs
6. Cultural sensitivity requirements

Respond with JSON:
{{
    "escalation_recommended": true/false,
    "confidence": 0.0-1.0,
    "reason": "specific reason for recommendation",
    "urgency": "low/medium/high",
    "human_skills_needed": ["skill1", "skill2"]
}}
"""
    
    def _build_quality_prompt(self, conversation_data: Dict[str, Any]) -> str:
        """构建质量分析提示词"""
        return f"""
Analyze the quality of this customer service conversation and provide improvement suggestions.

Conversation Data:
- Total Exchanges: {conversation_data.get('total_exchanges', 0)}
- Agent Responses: {len(conversation_data.get('agent_responses', {}))}
- Customer Sentiment: {conversation_data.get('sentiment', 'unknown')}
- Resolution Status: {conversation_data.get('resolution_status', 'pending')}
- Error Count: {conversation_data.get('error_count', 0)}

Evaluate:
1. Response relevance and helpfulness
2. Conversation flow and coherence
3. Customer satisfaction indicators
4. Technical accuracy
5. Cultural appropriateness

Respond with JSON:
{{
    "quality_score": 0.0-1.0,
    "improvement_areas": ["area1", "area2"],
    "strengths": ["strength1", "strength2"],
    "recommendations": ["rec1", "rec2"],
    "confidence": 0.0-1.0
}}
"""
    
    def _build_improvement_prompt(self, system_data: Dict[str, Any]) -> str:
        """构建改进建议提示词"""
        return f"""
Analyze this multi-agent customer service system and suggest improvements.

System Performance:
- Active Agents: {system_data.get('active_agents', 0)}
- Average Response Time: {system_data.get('avg_response_time', 0)}ms
- Error Rate: {system_data.get('error_rate', 0)}%
- Customer Satisfaction: {system_data.get('satisfaction_score', 0)}
- Daily Conversations: {system_data.get('daily_conversations', 0)}

Focus on:
1. Performance optimizations
2. User experience improvements
3. Agent coordination enhancements
4. Error reduction strategies
5. Scalability improvements

Respond with JSON:
{{
    "suggestions": [
        {{
            "category": "performance/ux/reliability",
            "title": "suggestion title",
            "description": "detailed description",
            "priority": "low/medium/high",
            "effort": "low/medium/high"
        }}
    ],
    "priority_areas": ["area1", "area2"],
    "complexity": "low/medium/high",
    "impact": "low/medium/high"
}}
"""
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """解析LLM升级分析响应"""
        try:
            return json.loads(response)
        except:
            # 提取关键信息的备用解析
            escalation_keywords = ["escalation", "human", "transfer", "handoff"]
            escalation_recommended = any(keyword in response.lower() for keyword in escalation_keywords)
            
            return {
                "escalation_recommended": escalation_recommended,
                "confidence": 0.5,
                "reason": "LLM analysis completed",
                "urgency": "medium",
                "human_skills_needed": []
            }
    
    def _parse_quality_response(self, response: str) -> Dict[str, Any]:
        """解析LLM质量分析响应"""
        try:
            return json.loads(response)
        except:
            return {
                "quality_score": 0.6,
                "improvement_areas": ["response_time", "personalization"],
                "strengths": ["accuracy", "completeness"],
                "recommendations": ["improve_context_awareness"],
                "confidence": 0.5
            }
    
    def _parse_improvement_response(self, response: str) -> Dict[str, Any]:
        """解析LLM改进建议响应"""
        try:
            return json.loads(response)
        except:
            return {
                "suggestions": [{
                    "category": "performance",
                    "title": "General system optimization",
                    "description": "Review and optimize system performance",
                    "priority": "medium",
                    "effort": "medium"
                }],
                "priority_areas": ["performance"],
                "complexity": "medium",
                "impact": "medium"
            }
    
    def _get_fallback_llm_result(self) -> Dict[str, Any]:
        """获取LLM分析的备用结果"""
        return {
            "escalation_recommended": False,
            "confidence": 0.5,
            "reason": "LLM analysis unavailable",
            "urgency": "medium",
            "human_skills_needed": [],
            "fallback": True
        }
    
    def _get_fallback_quality_result(self) -> Dict[str, Any]:
        """获取质量分析的备用结果"""
        return {
            "quality_score": 0.5,
            "improvement_areas": ["system_reliability"],
            "strengths": ["availability"],
            "recommendations": ["monitor_system_health"],
            "analysis_confidence": 0.3,
            "llm_analysis": False,
            "fallback": True
        }
    
    def _get_fallback_improvement_result(self) -> Dict[str, Any]:
        """获取改进建议的备用结果"""
        return {
            "suggestions": [],
            "priority_areas": [],
            "implementation_complexity": "unknown",
            "expected_impact": "unknown",
            "llm_generated": False,
            "fallback": True
        }
    
    def update_analysis_config(self, new_config: Dict[str, Any]) -> None:
        """
        更新分析配置
        
        参数:
            new_config: 新的配置参数
        """
        try:
            self.analysis_config.update(new_config)
            self.logger.info(f"LLM分析配置已更新: {new_config}")
        except Exception as e:
            self.logger.error(f"更新LLM分析配置失败: {e}")