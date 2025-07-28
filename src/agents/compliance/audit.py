"""
合规审计日志模块

该模块负责合规检查的审计日志记录和报告生成。
从主智能体中分离出来，专注于审计追踪和合规分析。

核心功能:
- 审计日志记录
- 合规报告生成
- 统计分析
- 监管审查支持
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime


class ComplianceAuditor:
    """
    合规审计器
    
    负责记录所有合规检查活动，生成审计报告，
    为监管审查和系统监控提供详细的追踪信息。
    
    属性:
        audit_log: 审计日志存储
        tenant_id: 租户标识符
        agent_id: 智能体标识符
        logger: 日志记录器
    """
    
    def __init__(self, tenant_id: str, agent_id: str):
        """
        初始化合规审计器
        
        参数:
            tenant_id: 租户标识符
            agent_id: 智能体标识符
        """
        self.tenant_id = tenant_id
        self.agent_id = agent_id
        self.audit_log: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(f"{__name__}.{agent_id}")
    
    def log_compliance_check(self, conversation_id: str, input_text: str, 
                           compliance_result: Dict[str, Any], processing_time_ms: float = 0.0):
        """
        记录合规检查到审计日志
        
        为监管审查和系统监控提供详细的审计追踪。
        保护用户隐私，只记录必要的统计信息。
        
        参数:
            conversation_id: 对话标识符
            input_text: 输入文本（仅记录hash以保护隐私）
            compliance_result: 合规检查结果
            processing_time_ms: 处理时间（毫秒）
        """
        log_entry = self._create_audit_entry(
            conversation_id, input_text, compliance_result, processing_time_ms
        )
        
        self.audit_log.append(log_entry)
        
        # 对重要事件进行系统日志记录
        self._log_to_system(compliance_result, conversation_id)
    
    def _create_audit_entry(self, conversation_id: str, input_text: str,
                           compliance_result: Dict[str, Any], processing_time_ms: float) -> Dict[str, Any]:
        """
        创建审计日志条目
        
        参数:
            conversation_id: 对话标识符
            input_text: 输入文本
            compliance_result: 合规检查结果
            processing_time_ms: 处理时间
            
        返回:
            Dict[str, Any]: 审计日志条目
        """
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "conversation_id": conversation_id,
            "tenant_id": self.tenant_id,
            "agent_id": self.agent_id,
            
            # 隐私保护：只记录文本特征，不记录原文
            "input_text_hash": hash(input_text),
            "input_length": len(input_text),
            "input_type": "text",  # 未来支持voice/image
            
            # 合规检查结果
            "compliance_status": compliance_result["status"],
            "violation_count": len(compliance_result["violations"]),
            "highest_severity": compliance_result["severity"],
            "categories_violated": compliance_result.get("categories_violated", []),
            
            # 性能指标
            "rules_checked": compliance_result["rules_checked"],
            "processing_time_ms": processing_time_ms,
            
            # 系统状态
            "fallback_applied": compliance_result.get("fallback_applied", False),
            "human_escalation": compliance_result["status"] in ["flagged", "blocked"]
        }
    
    def _log_to_system(self, compliance_result: Dict[str, Any], conversation_id: str):
        """
        记录到系统日志
        
        参数:
            compliance_result: 合规检查结果
            conversation_id: 对话标识符
        """
        status = compliance_result["status"]
        
        if status in ["flagged", "blocked"]:
            self.logger.warning(
                f"合规{status}: {conversation_id} - "
                f"{len(compliance_result['violations'])}个违规"
            )
        else:
            self.logger.debug(f"合规检查通过: {conversation_id}")
    
    def get_audit_summary(self, start_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        获取合规审计摘要报告
        
        生成指定时间范围内的合规审计统计报告，
        包括合规率、违规分类、风险评估等关键指标。
        
        参数:
            start_date: 可选的开始日期过滤
            
        返回:
            Dict[str, Any]: 审计摘要信息
        """
        relevant_logs = self._filter_logs_by_date(start_date)
        
        if not relevant_logs:
            return self._create_empty_summary()
        
        return self._generate_summary_report(relevant_logs, start_date)
    
    def _filter_logs_by_date(self, start_date: Optional[datetime]) -> List[Dict[str, Any]]:
        """
        按日期过滤审计日志
        
        参数:
            start_date: 开始日期
            
        返回:
            List[Dict[str, Any]]: 过滤后的日志列表
        """
        if not start_date:
            return self.audit_log
        
        return [
            log for log in self.audit_log 
            if datetime.fromisoformat(log["timestamp"]) >= start_date
        ]
    
    def _create_empty_summary(self) -> Dict[str, Any]:
        """
        创建空的摘要报告
        
        返回:
            Dict[str, Any]: 空摘要报告
        """
        return {
            "total_checks": 0,
            "compliance_rate": 100.0,
            "tenant_id": self.tenant_id,
            "agent_id": self.agent_id
        }
    
    def _generate_summary_report(self, logs: List[Dict[str, Any]], 
                               start_date: Optional[datetime]) -> Dict[str, Any]:
        """
        生成摘要报告
        
        参数:
            logs: 审计日志列表
            start_date: 开始日期
            
        返回:
            Dict[str, Any]: 摘要报告
        """
        total_checks = len(logs)
        status_counts = {}
        category_violations = {}
        
        # 统计分析
        for log in logs:
            status = log["compliance_status"]
            status_counts[status] = status_counts.get(status, 0) + 1
            
            for category in log.get("categories_violated", []):
                category_violations[category] = category_violations.get(category, 0) + 1
        
        compliance_rate = (status_counts.get("approved", 0) / total_checks * 100) if total_checks > 0 else 100.0
        
        return {
            "total_checks": total_checks,
            "status_distribution": status_counts,
            "category_violations": category_violations,
            "compliance_rate": compliance_rate,
            "risk_score": 100 - compliance_rate,  # 风险评分
            "tenant_id": self.tenant_id,
            "agent_id": self.agent_id,
            "reporting_period": {
                "start": start_date.isoformat() if start_date else None,
                "end": datetime.utcnow().isoformat()
            }
        }
    
    def get_audit_log_size(self) -> int:
        """
        获取审计日志大小
        
        返回:
            int: 日志条目数量
        """
        return len(self.audit_log)
    
    def clear_old_logs(self, days: int = 90):
        """
        清理过期的审计日志
        
        参数:
            days: 保留天数，默认90天
        """
        cutoff_date = datetime.utcnow() - datetime.timedelta(days=days)
        
        original_count = len(self.audit_log)
        self.audit_log = [
            log for log in self.audit_log
            if datetime.fromisoformat(log["timestamp"]) > cutoff_date
        ]
        
        cleared_count = original_count - len(self.audit_log)
        if cleared_count > 0:
            self.logger.info(f"清理了{cleared_count}条过期审计日志（超过{days}天）") 