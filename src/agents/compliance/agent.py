"""
合规审查智能体实现

该模块实现合规审查智能体，负责对所有客户输入进行合规性检查。
是多智能体系统的第一道防线，确保内容符合法规要求。

核心功能:
- 智能体主要接口和协调
- 消息处理和状态管理
- 模块间协调和错误处理
- 租户规则管理
"""

from typing import Dict, Any, Optional
from datetime import datetime

from ..base import BaseAgent, AgentMessage, ThreadState
from .rule_manager import ComplianceRuleManager
from .types import RuleSeverity, RuleAction
from .checker import ComplianceChecker
from .audit import ComplianceAuditor
from .metrics import ComplianceMetricsManager
from src.utils import get_current_datetime, get_processing_time_ms, format_timestamp
from src.llm import get_llm_client, get_prompt_manager, parse_structured_response
from src.llm.intelligent_router import RoutingStrategy


class ComplianceAgent(BaseAgent):
    """
    合规审查智能体
    
    作为客户输入的第一道防线，执行全面的合规性检查。
    支持多种监管要求，提供详细的审计追踪。
    
    采用模块化设计：
    - ComplianceChecker: 核心检查逻辑
    - ComplianceAuditor: 审计日志管理
    - ComplianceMetricsManager: 性能指标管理
    
    属性:
        rule_set: 合规规则集实例
        checker: 合规检查器
        auditor: 审计管理器
        metrics: 性能指标管理器
        tenant_rules: 租户特定规则
    """
    
    def __init__(self, tenant_id: str):
        """
        初始化合规审查智能体
        
        参数:
            tenant_id: 租户标识符，用于多租户规则隔离
        """
        # MAS架构：使用质量优化策略确保合规检查精确性
        super().__init__(
            agent_id=f"compliance_review_{tenant_id}", 
            tenant_id=tenant_id,
            routing_strategy=RoutingStrategy.PERFORMANCE_FIRST  # 合规检查需要高精度
        )
        
        # 初始化规则集
        self.rule_set = ComplianceRuleManager()
        
        # 初始化模块化组件
        self.checker = ComplianceChecker(self.rule_set, self.agent_id)
        self.auditor = ComplianceAuditor(tenant_id, self.agent_id)
        self.metrics = ComplianceMetricsManager(tenant_id, self.agent_id)
        
        # LLM integration for enhanced analysis
        self.llm_client = get_llm_client()
        self.prompt_manager = get_prompt_manager()
        
        # 租户特定配置
        self.tenant_rules: Dict[str, Any] = {}
        
        self.logger.info(f"合规审查智能体初始化完成: {self.agent_id}")
    
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """
        处理合规检查消息
        
        对单个消息执行合规性检查，返回检查结果。
        
        参数:
            message: 包含待检查文本的智能体消息
            
        返回:
            AgentMessage: 包含合规检查结果的响应消息
        """
        start_time = get_current_datetime()
        
        try:
            input_text = message.payload.get("text", "")
            
            # 执行合规检查
            compliance_result = await self.checker.perform_compliance_check(input_text)
            
            # 构建响应载荷
            response_payload = {
                "compliance_result": compliance_result,
                "original_text_hash": hash(input_text),
                "processing_agent": self.agent_id,
                "check_timestamp": format_timestamp(start_time)
            }
            
            # 更新统计和审计
            processing_time = get_processing_time_ms(start_time)
            self._update_metrics_and_audit(
                message.context.get("thread_id", "unknown"),
                input_text, 
                compliance_result, 
                processing_time
            )
            
            return await self.send_message(
                recipient=message.sender,
                message_type="response",
                payload=response_payload,
                context=message.context
            )
            
        except Exception as e:
            error_context = {
                "message_id": message.message_id,
                "sender": message.sender,
                "processing_agent": self.agent_id
            }
            error_info = await self.handle_error(e, error_context)
            
            # 更新错误指标
            self.metrics.update_status_metrics("error")
            
            # 返回错误响应
            return await self.send_message(
                recipient=message.sender,
                message_type="response",
                payload={"error": error_info, "compliance_result": {"status": "error"}},
                context=message.context
            )
    
    async def process_conversation(self, state: ThreadState) -> ThreadState:
        """
        处理对话状态中的合规检查
        
        在LangGraph工作流中执行合规审查，更新对话状态。
        
        参数:
            state: 当前对话状态
            
        返回:
            ThreadState: 更新后的对话状态
        """
        start_time = get_current_datetime()
        
        try:
            customer_input = state.customer_input
            
            # 执行综合合规检查 (规则 + LLM分析)
            compliance_result = await self._enhanced_compliance_check(customer_input)
            
            # 更新对话状态
            state.compliance_result = compliance_result
            state.active_agents.append(self.agent_id)
            
            # 根据合规结果确定后续处理
            self._update_conversation_state(state, compliance_result)
            
            # 更新统计和审计
            processing_time = get_processing_time_ms(start_time)
            self._update_metrics_and_audit(
                state.thread_id,
                customer_input,
                compliance_result,
                processing_time
            )
            
            return state
            
        except Exception as e:
            error_context = {
                "thread_id": state.thread_id,
                "customer_input_length": len(state.customer_input),
                "tenant_id": state.tenant_id,
                "agent": self.agent_id
            }
            await self.handle_error(e, error_context)
            
            # 设置安全的默认状态
            self._set_error_state(state)
            
            return state
    
    def _update_conversation_state(self, state: ThreadState, 
                                 compliance_result: Dict[str, Any]):
        """
        根据合规结果更新对话状态
        
        参数:
            state: 对话状态
            compliance_result: 合规检查结果
        """
        status = compliance_result["status"]
        
        if status == "blocked":
            state.error_state = "compliance_violation"
            state.final_response = compliance_result["user_message"]
            state.processing_complete = True
            state.human_escalation = False  # 直接阻止，无需人工干预
            
        elif status == "flagged":
            # 标记需要人工审核但继续处理
            state.human_escalation = True
    
    def _set_error_state(self, state: ThreadState):
        """
        设置错误状态
        
        参数:
            state: 对话状态
        """
        state.compliance_result = {
            "status": "error",
            "message": "合规检查系统暂时不可用",
            "fallback_applied": True,
            "agent_id": self.agent_id
        }
        
        # 出错时采用保守策略，标记为需要人工审核
        state.human_escalation = True
        
        # 更新错误指标
        self.metrics.update_status_metrics("error")
    
    def _update_metrics_and_audit(self, thread_id: str, input_text: str,
                                compliance_result: Dict[str, Any], processing_time_ms: float):
        """
        更新指标和审计信息
        
        参数:
            thread_id: 对话ID
            input_text: 输入文本
            compliance_result: 合规结果
            processing_time_ms: 处理时间
        """
        # 更新性能指标
        self.metrics.update_processing_stats(processing_time_ms)
        self.metrics.update_status_metrics(compliance_result["status"])
        
        # 记录审计日志
        self.auditor.log_compliance_check(
            thread_id, input_text, compliance_result, processing_time_ms
        )
        
        # 更新基类统计
        self.update_stats(processing_time_ms)
    
    def add_tenant_rule(self, rule) -> bool:
        """
        添加租户特定的合规规则
        
        参数:
            rule: 合规规则对象
            
        返回:
            bool: 添加是否成功
        """
        rule.tenant_specific = True
        success = self.rule_set.add_rule(rule)
        
        if success:
            self.logger.info(f"添加租户规则: {rule.rule_id} for {self.tenant_id}")
        else:
            self.logger.warning(f"租户规则添加失败: {rule.rule_id}")
        
        return success
    
    def get_audit_summary(self, start_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        获取合规审计摘要报告
        
        参数:
            start_date: 可选的开始日期过滤
            
        返回:
            Dict[str, Any]: 审计摘要信息
        """
        return self.auditor.get_audit_summary(start_date)
    
    def get_compliance_stats(self) -> Dict[str, Any]:
        """
        获取合规检查统计信息
        
        返回:
            Dict[str, Any]: 统计信息
        """
        return self.metrics.get_compliance_stats(
            rule_set_stats=self.rule_set.get_statistics(),
            audit_log_size=self.auditor.get_audit_log_size(),
            is_active=self.is_active
        )
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        获取合规系统健康状态
        
        返回:
            Dict[str, Any]: 健康状态信息
        """
        return self.metrics.get_health_status()
    
    async def _enhanced_compliance_check(self, customer_input: str) -> Dict[str, Any]:
        """
        执行增强的合规检查 (规则 + LLM分析)
        
        结合传统规则检查和LLM智能分析，提供更准确的合规评估。
        
        参数:
            customer_input: 客户输入文本
            
        返回:
            Dict[str, Any]: 综合合规检查结果
        """
        try:
            # 1. 执行传统规则检查 (快速、确定性)
            rule_result = await self.checker.perform_compliance_check(customer_input)
            
            # 2. 如果规则检查已经阻止，直接返回
            if rule_result.get("status") == "blocked":
                rule_result["analysis_method"] = "rule_based"
                return rule_result
            
            # 3. 执行LLM增强分析 (上下文感知、细致)
            llm_result = await self._llm_compliance_analysis(customer_input)
            
            # 4. 合并规则和LLM分析结果
            return self._merge_compliance_results(rule_result, llm_result)
            
        except Exception as e:
            self.logger.error(f"增强合规检查失败: {e}")
            # 降级到纯规则检查
            fallback_result = await self.checker.perform_compliance_check(customer_input)
            fallback_result["analysis_method"] = "rule_fallback"
            fallback_result["llm_error"] = str(e)
            return fallback_result
    
    async def _llm_compliance_analysis(self, customer_input: str) -> Dict[str, Any]:
        """
        使用LLM进行合规分析
        
        参数:
            customer_input: 客户输入文本
            
        返回:
            Dict[str, Any]: LLM分析结果
        """
        try:
            # 获取合规分析提示词
            prompt = self.prompt_manager.get_prompt(
                "compliance", 
                "content_analysis",
                customer_input=customer_input
            )
            
            # 调用LLM分析
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm_client.chat_completion(messages, temperature=0.3)
            
            # 解析结构化响应
            return parse_structured_response(response, "compliance")
            
        except Exception as e:
            self.logger.warning(f"LLM合规分析失败: {e}")
            return {
                "status": "approved",
                "violations": [],
                "severity": "low",
                "user_message": "",
                "recommended_action": "proceed",
                "llm_fallback": True
            }
    
    def _merge_compliance_results(self, rule_result: Dict[str, Any], llm_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并规则检查和LLM分析结果
        
        参数:
            rule_result: 规则检查结果
            llm_result: LLM分析结果
            
        返回:
            Dict[str, Any]: 综合分析结果
        """
        # 以更严格的状态为准
        rule_status = rule_result.get("status", "approved")
        llm_status = llm_result.get("status", "approved")
        
        status_priority = {"blocked": 3, "flagged": 2, "approved": 1}
        final_status = rule_status if status_priority.get(rule_status, 1) >= status_priority.get(llm_status, 1) else llm_status
        
        # 合并违规信息
        rule_violations = rule_result.get("violations", [])
        llm_violations = llm_result.get("violations", [])
        combined_violations = list(set(rule_violations + llm_violations))
        
        # 综合严重性评估
        rule_severity = rule_result.get("severity", "low")
        llm_severity = llm_result.get("severity", "low")
        severity_priority = {"high": 3, "medium": 2, "low": 1}
        final_severity = rule_severity if severity_priority.get(rule_severity, 1) >= severity_priority.get(llm_severity, 1) else llm_severity
        
        return {
            "status": final_status,
            "violations": combined_violations,
            "severity": final_severity,
            "user_message": llm_result.get("user_message", rule_result.get("user_message", "")),
            "recommended_action": llm_result.get("recommended_action", rule_result.get("recommended_action", "proceed")),
            "analysis_method": "hybrid",
            "rule_analysis": rule_result,
            "llm_analysis": llm_result,
            "agent_id": self.agent_id
        } 