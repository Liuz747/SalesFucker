"""
Token管理工具模块

提供统一的Token处理和管理功能，消除各Agent中重复的Token处理逻辑。

核心功能:
- 统一的Token提取方法，兼容所有LLM提供商
- Agent Token使用情况聚合
- 工作流级别的Token统计
- 标准化的Token数据结构
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class TokenUsage:
    """Token使用情况数据结构"""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def __add__(self, other: 'TokenUsage') -> 'TokenUsage':
        """TokenUsage相加运算"""
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            total_tokens=self.total_tokens + other.total_tokens
        )


@dataclass
class AgentTokenSummary:
    """单个Agent的Token使用汇总"""
    agent_id: str
    agent_type: str
    token_usage: TokenUsage
    response_length: int
    timestamp: str


@dataclass
class WorkflowTokenSummary:
    """工作流的Token使用汇总"""
    total_tokens: int
    total_input_tokens: int
    total_output_tokens: int
    agent_summaries: List[AgentTokenSummary]
    agent_count: int

    @classmethod
    def from_agent_summaries(cls, summaries: List[AgentTokenSummary]) -> 'WorkflowTokenSummary':
        """从Agent汇总创建工作流汇总"""
        total_usage = TokenUsage()
        for summary in summaries:
            total_usage = total_usage + summary.token_usage

        return cls(
            total_tokens=total_usage.total_tokens,
            total_input_tokens=total_usage.input_tokens,
            total_output_tokens=total_usage.output_tokens,
            agent_summaries=summaries,
            agent_count=len(summaries)
        )


class TokenManager:
    """
    考虑到不同模型api对token字段的返回不同，这里提供一个统一的Token管理器

    提供Token提取、聚合和统计功能，消除各Agent中重复的Token处理逻辑。
    """

    @staticmethod
    def extract_tokens(llm_response: Any) -> TokenUsage:
        """
        从LLM响应中提取Token使用信息

        兼容不同LLM提供商的响应格式
        参数:
            llm_response: LLM的响应对象

        返回:
            TokenUsage: 标准化的Token使用信息
        """
        if not llm_response:
            return TokenUsage()

        # 尝试从不同格式的响应中提取usage信息
        usage = None

        # 格式1: 对象有usage属性
        if hasattr(llm_response, 'usage'):
            usage = getattr(llm_response, 'usage')

        # 格式2: 字典格式有usage键
        elif isinstance(llm_response, dict) and 'usage' in llm_response:
            usage = llm_response['usage']

        # 格式3: 直接是usage字典
        elif isinstance(llm_response, dict) and any(key in llm_response for key in ['input_tokens', 'output_tokens', 'total_tokens']):
            usage = llm_response

        if usage and isinstance(usage, dict):
            input_tokens = usage.get('input_tokens', usage.get('prompt_tokens', 0))
            output_tokens = usage.get('output_tokens', usage.get('completion_tokens', 0))
            total_tokens = usage.get('total_tokens', input_tokens + output_tokens)

            return TokenUsage(
                input_tokens=max(0, int(input_tokens)),
                output_tokens=max(0, int(output_tokens)),
                total_tokens=max(0, int(total_tokens))
            )

        return TokenUsage()

    @staticmethod
    def extract_agent_token_info(agent_id: str, agent_type: str, llm_response: Any,
                               response_content: str, timestamp: str) -> Dict[str, Any]:
        """
        提取Agent的Token信息并返回标准化格式

        参数:
            agent_id: Agent ID
            agent_type: Agent类型 (如 'sentiment', 'sales')
            llm_response: LLM响应对象
            response_content: 响应内容
            timestamp: 时间戳

        返回:
            Dict: 包含Token信息的标准化字典
        """
        token_usage = TokenManager.extract_tokens(llm_response)

        return {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "response": response_content,
            "token_usage": {
                "input_tokens": token_usage.input_tokens,
                "output_tokens": token_usage.output_tokens,
                "total_tokens": token_usage.total_tokens
            },
            "tokens_used": token_usage.total_tokens,  # 向后兼容
            "response_length": len(response_content),
            "timestamp": timestamp
        }

    @staticmethod
    def aggregate_agent_tokens(agent_responses: Dict[str, Any]) -> WorkflowTokenSummary:
        """
        聚合所有Agent的Token使用情况

        参数:
            agent_responses: Agent响应字典 {agent_id: response_data}

        返回:
            WorkflowTokenSummary: 工作流级别的Token使用汇总
        """
        agent_summaries = []

        for agent_id, response_data in agent_responses.items():
            if not isinstance(response_data, dict):
                continue

            # 提取Token信息
            token_usage_data = response_data.get('token_usage', {})
            if not token_usage_data and 'tokens_used' in response_data:
                # 向后兼容：如果没有token_usage但有tokens_used
                token_usage_data = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": response_data.get("tokens_used", 0)
                }

            token_usage = TokenUsage(
                input_tokens=token_usage_data.get("input_tokens", 0),
                output_tokens=token_usage_data.get("output_tokens", 0),
                total_tokens=token_usage_data.get("total_tokens", 0)
            )

            agent_summary = AgentTokenSummary(
                agent_id=agent_id,
                agent_type=response_data.get("agent_type", "unknown"),
                token_usage=token_usage,
                response_length=response_data.get("response_length", 0),
                timestamp=response_data.get("timestamp", "")
            )

            agent_summaries.append(agent_summary)

        return WorkflowTokenSummary.from_agent_summaries(agent_summaries)

    @staticmethod
    def update_workflow_state_with_tokens(state: Dict[str, Any],
                                        agent_responses: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新工作流状态，添加Token聚合信息

        参数:
            state: 工作流状态字典
            agent_responses: Agent响应字典

        返回:
            Dict: 更新后的工作流状态
        """
        token_summary = TokenManager.aggregate_agent_tokens(agent_responses)

        # 更新工作流级别的Token信息
        state["total_tokens"] = token_summary.total_tokens
        state["token_summary"] = {
            "total_tokens": token_summary.total_tokens,
            "total_input_tokens": token_summary.total_input_tokens,
            "total_output_tokens": token_summary.total_output_tokens,
            "agent_count": token_summary.agent_count,
            "agent_details": [
                {
                    "agent_id": summary.agent_id,
                    "agent_type": summary.agent_type,
                    "tokens_used": summary.token_usage.total_tokens,
                    "input_tokens": summary.token_usage.input_tokens,
                    "output_tokens": summary.token_usage.output_tokens,
                    "response_length": summary.response_length,
                    "timestamp": summary.timestamp
                }
                for summary in token_summary.agent_summaries
            ]
        }

        return state