import os

from langgraph.graph import StateGraph, START, END

from config import mas_config
from core.agents import BaseAgent
from core.entities import WorkflowExecutionModel
from libs.types import AgentNodeType
from utils import get_component_logger
from utils.llm_debug_wrapper import LLMDebugWrapper
from .base_workflow import BaseWorkflow

logger = get_component_logger(__name__)

# 并行执行配置开关
ENABLE_PARALLEL_EXECUTION = os.getenv("ENABLE_PARALLEL_EXECUTION", "true").lower() == "true"


class ChatWorkflow(BaseWorkflow):
    """
    聊天工作流 - 支持并行节点架构

    实现具体的聊天对话流程，包括情感分析、意向分析和销售处理。

    并行架构特点：
    - 并行执行：sentiment和intent节点同时运行
    - 状态安全合并：使用LangGraph Reducer机制避免并发更新冲突
    - 智能状态管理：每个agent写入专用字段，Reducer自动合并最终状态
    - 错误隔离：单个并行节点失败不影响其他节点和整体流程

    工作流程（并行模式）：
    START → [sentiment, intent] (并行) → sales → END

    工作流程（顺序模式）：
    START → sentiment → intent → sales → END

    特性：
    - 记忆管理已下沉到各智能体内部
    - 智能体节点处理与错误恢复
    - 降级处理策略
    - 并行处理优化（基于Reducer机制）
    - 状态汇合机制
    - 可配置执行模式（并行/顺序）
    """

    def __init__(self, agents: dict[AgentNodeType, BaseAgent]):
        """
        初始化聊天工作流

        Args:
            agents: 智能体字典，需要包含所有必要的节点agents
        """
        super().__init__(agents)
        self.enable_parallel = ENABLE_PARALLEL_EXECUTION
        
        # 自动根据全局日志级别决定是否启用LLM调试日志
        # 当日志级别为DEBUG时，自动包装LLM客户端以记录详细的输入输出
        if mas_config.LOG_LEVEL.upper() == "DEBUG":
            self._enable_debug_logging()

        logger.info(f"ChatWorkflow初始化完成，并行执行模式: {self.enable_parallel}")

    def _enable_debug_logging(self):
        """为所有agent启用调试日志记录"""
        for name, agent in self.agents.items():
            if not isinstance(agent.llm_client, LLMDebugWrapper):
                agent.llm_client = LLMDebugWrapper(agent.llm_client, name, logger)
                logger.debug(f"已为Agent节点 {name} 启用LLM调试日志")

    def register_nodes(self, graph: StateGraph):
        """
        注册工作流节点 - 支持并行和顺序两种执行模式

        根据配置选择执行模式：
        - 并行模式：使用LangGraph的Reducer机制实现真正的并行执行
        - 顺序模式：传统的串行执行，确保兼容性

        参数:
            graph: 要注册节点的状态图
        """
        # 注册所有智能体节点
        for node_name in self.agents.keys():
            graph.add_node(node_name, self._create_agent_node(node_name))

        logger.debug(f"已注册 {len(self.agents)} 个工作流节点，执行模式: {'并行' if self.enable_parallel else '顺序'}")

    def define_edges(self, graph: StateGraph):
        """
        定义节点间连接边 - 支持并行和顺序两种执行模式

        根据配置定义不同的执行流程：
        - 并行模式：START节点同时触发多个并行节点
        - 顺序模式：传统的串行执行

        参数:
            graph: 要定义边的状态图
        """
        if self.enable_parallel:
            # 并行执行模式：START同时触发两个并行节点
            parallel_nodes = [
                AgentNodeType.SENTIMENT,
                AgentNodeType.INTENT
            ]

            # START → 并行节点组（同时执行）
            for node in parallel_nodes:
                graph.add_edge(START, node)

            # 并行节点 → Sales节点
            for node in parallel_nodes:
                graph.add_edge(node, AgentNodeType.SALES)

            # 销售节点 → END
            graph.add_edge(AgentNodeType.SALES, END)

            logger.debug("并行执行架构边定义完成 - START → [sentiment, intent] → sales → END")
        else:
            # 顺序执行模式
            graph.add_edge(AgentNodeType.SENTIMENT, AgentNodeType.INTENT)
            graph.add_edge(AgentNodeType.INTENT, AgentNodeType.SALES)
            logger.debug("顺序执行架构边定义完成 - sentiment → intent → sales")

    def set_entry_exit_points(self, graph: StateGraph):
        """
        设置工作流入口和出口点 - 支持两种执行模式

        根据配置设置不同的入口出口点：
        - 并行模式：已在_define_edges中通过START/END设置
        - 顺序模式：使用传统的set_entry_point/set_finish_point

        参数:
            graph: 要设置入口出口的状态图
        """
        if not self.enable_parallel:
            # 顺序模式需要显式设置入口出口点
            graph.set_entry_point(AgentNodeType.SENTIMENT)
            graph.set_finish_point(AgentNodeType.SALES)
            logger.debug("顺序执行架构入口出口点设置完成 - sentiment → sales")
        else:
            # 并行模式的入口出口点已在_define_edges中通过START/END设置
            logger.debug("并行执行架构入口出口点已通过START/END设置")
    
    async def _process_agent_node(
            self,
            state: WorkflowExecutionModel,
            node_name: AgentNodeType
    ) -> dict:
        """
        通用智能体节点处理方法

        统一处理智能体调用和错误处理。支持并发状态管理。

        参数:
            state: 当前对话状态
            node_name: 节点名称

        返回:
            dict: 状态更新增量（LangGraph会通过Reducer自动合并）
        """
        agent = self.agents.get(node_name)
        if not agent:
            logger.error(f"Agent未找到: {node_name}")
            raise ValueError(f"Agent未找到: '{node_name}'")

        try:
            result_state = await agent.process_conversation(state)

            if not isinstance(result_state, dict):
                logger.warning(f"Agent {node_name} 返回非字典结果: {type(result_state)}")
                return {"input_tokens": 0, "output_tokens": 0}

            logger.debug(f"节点 {node_name} 执行完成")

            # 直接返回agent的结果，LangGraph的Reducer会自动处理合并
            return result_state

        except Exception as e:
            logger.error(f"节点 {node_name} 处理错误: {e}", exc_info=True)
            # 即使出错也返回token字段，避免阻塞其他并行节点
            return {"input_tokens": 0, "output_tokens": 0}

    def _create_agent_node(self, node_name: AgentNodeType):
        """创建Agent节点的通用方法"""
        async def agent_node(state: WorkflowExecutionModel) -> dict:
            return await self._process_agent_node(state, node_name)
        return agent_node
