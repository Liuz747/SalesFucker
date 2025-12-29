"""
数字员工聊天工作流

实现聊天对话的具体工作流逻辑，包括节点处理、条件路由和状态管理。
支持并行节点执行，提升处理效率和智能分析能力。
"""

import os
from uuid import uuid4

from langgraph.graph import StateGraph, START, END

from config import mas_config
from core.agents.base import BaseAgent
from libs.constants import AgentNodes
from utils import get_component_logger
from utils.llm_debug_wrapper import LLMDebugWrapper
from .base_workflow import BaseWorkflow

logger = get_component_logger(__name__)

# 并行执行配置开关
ENABLE_PARALLEL_EXECUTION = os.getenv("ENABLE_PARALLEL_EXECUTION", "true").lower() == "true"

class ChatWorkflow(BaseWorkflow):
    """
    聊天工作流 - 支持真正并行节点架构

    实现具体的聊天对话流程，包括情感分析、邀约意向分析、素材意向分析和销售处理。

    并行架构特点：
    - 真正并行执行：sentiment_analysis、intent_analysis同时运行
    - 状态安全合并：使用LangGraph Reducer机制避免并发更新冲突
    - 智能状态管理：每个agent写入专用字段，通过Reducer合并最终状态
    - 错误隔离：单个并行节点失败不影响其他节点和整体流程

    工作流程（并行模式）：
    START → parallel_coordinator → [并行节点组] → result_aggregator → sales_agent → END

    工作流程（顺序模式）：
    START → sentiment_analysis → intent_analysis → sales_agent → END

    记忆管理已下沉到各智能体内部，不再依赖工作流层级的统一处理。

    包含增强的节点处理能力：
    - 智能体节点处理与错误恢复
    - 降级处理策略
    - 并行处理优化（基于Reducer机制）
    - 状态汇合机制
    - 可配置执行模式（并行/顺序）
    """

    def __init__(self, agents: dict[str, "BaseAgent"]):
        """
        初始化聊天工作流

        Args:
            agents: 智能体字典，需要包含所有必要的节点agents
        """
        self.agents = agents
        self.enable_parallel = ENABLE_PARALLEL_EXECUTION
        
        # 自动根据全局日志级别决定是否启用LLM调试日志
        # 当日志级别为DEBUG时，自动包装LLM客户端以记录详细的输入输出
        if mas_config.LOG_LEVEL.upper() == "DEBUG":
            self._enable_debug_logging()

        logger.info(f"ChatWorkflow初始化完成，并行执行模式: {self.enable_parallel}")

    def _enable_debug_logging(self):
        """为所有agent启用调试日志记录"""
        for name, agent in self.agents.items():
            if hasattr(agent, 'llm_client') and agent.llm_client:
                # 避免重复包装
                if not isinstance(agent.llm_client, LLMDebugWrapper):
                    agent.llm_client = LLMDebugWrapper(agent.llm_client, name, logger)
                    logger.debug(f"已为节点 {name} 启用LLM调试日志")

    def build_graph(self):
        """
        构建并返回工作流图

        使用LangGraph编译时状态定义，确保Reducer函数正确应用。
        """
        from core.entities import WorkflowExecutionModel

        # 使用编译时状态定义构建图
        graph = StateGraph(WorkflowExecutionModel)

        # 注册节点
        self._register_nodes(graph)

        # 定义边
        self._define_edges(graph)

        # 设置入口出口点
        self._set_entry_exit_points(graph)

        # 编译图，应用Reducer函数
        compiled_graph = graph.compile()

        return compiled_graph
    
    def _register_nodes(self, graph: StateGraph):
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

        # 如果启用并行模式，添加额外的并行控制节点
        if self.enable_parallel:
            # 并行协调节点 - 准备并行执行环境
            graph.add_node("parallel_coordinator", self._create_parallel_coordinator_node())
            # 结果聚合节点 - 合并并行节点结果
            graph.add_node("result_aggregator", self._create_result_aggregator_node())

            logger.debug(f"已注册 {len(self.agents) + 2} 个工作流节点，采用并行执行架构")
        else:
            logger.debug(f"已注册 {len(self.agents)} 个工作流节点，采用顺序执行架构")
    
    def _define_edges(self, graph: StateGraph):
        """
        定义节点间连接边 - 支持并行和顺序两种执行模式

        根据配置定义不同的执行流程：
        - 并行模式：使用START/END和并行控制节点
        - 顺序模式：传统的边连接

        参数:
            graph: 要定义边的状态图
        """
        if self.enable_parallel:
            # 并行执行模式
            parallel_nodes = [
                AgentNodes.SENTIMENT_NODE,
                AgentNodes.INTENT_NODE,
                # AgentNodes.APPOINTMENT_INTENT_NODE,
                # AgentNodes.MATERIAL_INTENT_NODE
            ]

            # START → 并行协调节点
            graph.add_edge(START, "parallel_coordinator")

            # 协调节点 → 并行节点组
            for node in parallel_nodes:
                graph.add_edge("parallel_coordinator", node)

            # 并行节点组 → 结果聚合节点
            for node in parallel_nodes:
                graph.add_edge(node, "result_aggregator")

            # 结果聚合节点 → 销售节点
            graph.add_edge("result_aggregator", AgentNodes.SALES_NODE)

            # 销售节点 → END
            graph.add_edge(AgentNodes.SALES_NODE, END)

            logger.debug("并行执行架构边定义完成 - START → coordinator → [并行节点组] → aggregator → sales → END")
        else:
            # 顺序执行模式
            graph.add_edge(AgentNodes.SENTIMENT_NODE, AgentNodes.INTENT_NODE)
            graph.add_edge(AgentNodes.INTENT_NODE, AgentNodes.SALES_NODE)
            logger.debug("顺序执行架构边定义完成 - sentiment → intent_analysis → sales")

            # graph.add_edge(AgentNodes.SENTIMENT_NODE, AgentNodes.APPOINTMENT_INTENT_NODE)
            # graph.add_edge(AgentNodes.APPOINTMENT_INTENT_NODE, AgentNodes.MATERIAL_INTENT_NODE)
            # graph.add_edge(AgentNodes.MATERIAL_INTENT_NODE, AgentNodes.SALES_NODE)
    
    def _set_entry_exit_points(self, graph: StateGraph):
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
            graph.set_entry_point(AgentNodes.SENTIMENT_NODE)
            graph.set_finish_point(AgentNodes.SALES_NODE)
            logger.debug("顺序执行架构入口出口点设置完成 - sentiment → sales")
        else:
            # 并行模式的入口出口点已在_define_edges中通过START/END设置
            logger.debug("并行执行架构入口出口点已通过START/END设置")
    
    async def _process_agent_node(self, state, node_name: str) -> dict:
        """
        通用智能体节点处理方法

        统一处理智能体调用和错误处理，支持LangGraph的并发状态管理。

        参数:
            state: 当前对话状态
            node_name: 节点名称

        返回:
            dict: 更新后的状态（返回增量更新，LangGraph会自动合并）
        """
        agent = self.agents.get(node_name)
        if not agent:
            logger.error(f"智能体未找到: {node_name}")
            raise ValueError(f"Agent '{node_name}' not found")

        try:
            result_state = await agent.process_conversation(state)

            if not isinstance(result_state, dict):
                logger.warning(f"Agent {node_name} 返回非字典结果: {type(result_state)}")
                return {}

            # 构建状态更新 - 每个agent只更新自己的专用字段
            update_dict = {}

            # 根据节点类型提取专用字段
            if node_name == AgentNodes.SENTIMENT_NODE:
                if "sentiment_analysis" in result_state:
                    update_dict["sentiment_analysis"] = result_state["sentiment_analysis"]
                if "journey_stage" in result_state:
                    update_dict["journey_stage"] = result_state["journey_stage"]
                if "matched_prompt" in result_state:
                    update_dict["matched_prompt"] = result_state["matched_prompt"]

            elif node_name == AgentNodes.APPOINTMENT_INTENT_NODE:
                if "appointment_intent" in result_state:
                    update_dict["appointment_intent"] = result_state["appointment_intent"]
                if "business_outputs" in result_state:
                    update_dict["business_outputs"] = result_state["business_outputs"]

            elif node_name == AgentNodes.MATERIAL_INTENT_NODE:
                if "material_intent" in result_state:
                    update_dict["material_intent"] = result_state["material_intent"]

            elif node_name == AgentNodes.INTENT_NODE:
                # 统一意向分析节点 - 处理新的intent_analysis字段
                if "intent_analysis" in result_state:
                    update_dict["intent_analysis"] = result_state["intent_analysis"]
                    # 从intent_analysis中提取到独立字段（供其他agents使用）
                    intent_data = result_state["intent_analysis"]
                    if "assets_intent" in intent_data:
                        update_dict["material_intent"] = intent_data["assets_intent"]
                    if "appointment_intent" in intent_data:
                        update_dict["appointment_intent"] = intent_data["appointment_intent"]
                if "business_outputs" in result_state:
                    update_dict["business_outputs"] = result_state["business_outputs"]

            elif node_name == AgentNodes.SALES_NODE:
                if "sales_response" in result_state:
                    update_dict["sales_response"] = result_state["sales_response"]
                if "output" in result_state:
                    update_dict["output"] = result_state["output"]
                if "total_tokens" in result_state:
                    update_dict["total_tokens"] = result_state["total_tokens"]

            # 统一处理agent_responses收集器 - 直接使用agent返回的values
            # 这里的关键是：agent已经将自己的结果正确写入了values['agent_responses']中
            # 我们只需要确保这个values字段被包含在返回的更新字典中，不要覆盖它
            if isinstance(result_state, dict) and "values" in result_state:
                update_dict["values"] = result_state["values"]
            else:
                # 只有当agent没有返回values时（异常情况），才尝试手动构造
                values_update = (state.values or {}).copy() if state.values else {}
                
                if "agent_responses" not in values_update:
                    values_update["agent_responses"] = {}

                # 只有当result_state看起来不像完整状态时才添加
                # 避免将整个状态树作为agent响应
                is_full_state = "workflow_id" in result_state or "thread_id" in result_state
                if not is_full_state:
                    values_update["agent_responses"][node_name] = result_state
                    update_dict["values"] = values_update

            # 更新活跃agents列表
            if "active_agents" in result_state:
                update_dict["active_agents"] = result_state["active_agents"]
            else:
                current_active = state.active_agents or []
                if node_name not in current_active:
                    update_dict["active_agents"] = current_active + [node_name]

            # 统一传递 Token 统计字段
            update_dict["input_tokens"] = result_state.get("input_tokens", 0)
            update_dict["output_tokens"] = result_state.get("output_tokens", 0)

            logger.debug(f"节点 {node_name} 执行完成，更新状态字段: {list(update_dict.keys())}")
            return update_dict

        except Exception as e:
            logger.error(f"节点 {node_name} 处理错误: {e}", exc_info=True)
            # 即使出错也返回token字段，避免阻塞其他并行节点
            return {"input_tokens": 0, "output_tokens": 0}

    def _create_agent_node(self, node_name: str):
        """创建智能体节点的通用方法"""
        async def agent_node(state) -> dict:
            return await self._process_agent_node(state, node_name)
        return agent_node

    def _create_parallel_coordinator_node(self):
        """
        创建并行协调节点

        负责准备并行执行环境，初始化状态收集器。
        """
        async def parallel_coordinator(state) -> dict:
            """并行协调节点处理逻辑"""
            logger.debug("并行协调节点开始执行")

            try:
                # 确保状态是字典类型
                if hasattr(state, 'model_dump'):
                    state_dict = state.model_dump(mode='json')
                else:
                    state_dict = state if isinstance(state, dict) else {"state": str(state)}

                # 初始化并行执行上下文
                parallel_nodes_list = [
                    AgentNodes.SENTIMENT_NODE,
                    AgentNodes.INTENT_NODE,
                    # AgentNodes.APPOINTMENT_INTENT_NODE,
                    # AgentNodes.MATERIAL_INTENT_NODE
                ]

                parallel_context = {
                    "execution_id": str(uuid4()),
                    "parallel_nodes": parallel_nodes_list,
                    "execution_status": "initiated",
                    "started_at": state_dict.get("started_at", "")
                }

                # 初始化状态收集器 - 确保总是字典类型
                values_update = state_dict.get("values") or {}
                if values_update is None:
                    values_update = {}
                elif not isinstance(values_update, dict):
                    values_update = {"original_values": str(values_update)}

                values_update.update({
                    "parallel_execution": parallel_context,
                    "agent_responses": {}  # 初始化agent响应收集器
                })

                logger.debug(f"并行协调节点完成 - 执行ID: {parallel_context['execution_id']}")
                return {"values": values_update}

            except Exception as e:
                logger.error(f"并行协调节点执行失败: {e}", exc_info=True)
                # 即使出错也要让流程继续
                return {"values": {"parallel_execution": {"execution_status": "failed", "error": str(e)}}}

        return parallel_coordinator

    def _create_result_aggregator_node(self):
        """
        创建结果聚合节点

        负责合并并行节点的执行结果，为sales_agent准备完整的上下文。
        """
        async def result_aggregator(state) -> dict:
            """结果聚合节点处理逻辑"""
            logger.debug("结果聚合节点开始执行")

            try:
                # 确保状态是字典类型
                if hasattr(state, 'model_dump'):
                    state_dict = state.model_dump(mode='json')
                else:
                    state_dict = state if isinstance(state, dict) else {"state": str(state)}

                # 收集所有并行节点的结果
                aggregated_results = {}
                parallel_nodes = [
                    AgentNodes.SENTIMENT_NODE,
                    AgentNodes.INTENT_NODE,
                    # AgentNodes.APPOINTMENT_INTENT_NODE,
                    # AgentNodes.MATERIAL_INTENT_NODE
                ]

                # 从状态中提取各节点的结果
                for node_name in parallel_nodes:
                    if node_name == AgentNodes.INTENT_NODE:
                        # 统一意向节点 - 提取intent_analysis, material_intent, appointment_intent
                        if "intent_analysis" in state_dict and state_dict["intent_analysis"] is not None:
                            aggregated_results["intent_analysis"] = state_dict["intent_analysis"]
                        if "material_intent" in state_dict and state_dict["material_intent"] is not None:
                            aggregated_results["assets_intent"] = state_dict["material_intent"]
                        if "appointment_intent" in state_dict and state_dict["appointment_intent"] is not None:
                            aggregated_results["appointment_intent"] = state_dict["appointment_intent"]
                        if "business_outputs" in state_dict and state_dict["business_outputs"] is not None:
                            aggregated_results["business_outputs"] = state_dict["business_outputs"]
                    # field_name = node_name.replace("_analysis", "") if "analysis" in node_name else node_name
                    # if field_name == "sentiment":
                    #     field_name = "sentiment_analysis"
                    # elif field_name == "appointment":
                    #     field_name = "appointment_intent"
                    # elif field_name == "material":
                    #     field_name = "material_intent"

                    # if field_name in state_dict and state_dict[field_name] is not None:
                    #     aggregated_results[field_name] = state_dict[field_name]

                # 更新聚合状态
                values_update = state_dict.get("values", {})
                values_update.update({
                    "aggregated_results": aggregated_results,
                    "parallel_completed": True,
                    "completion_time": state_dict.get("started_at", "")
                })

                logger.debug(f"结果聚合完成，聚合了 {len(aggregated_results)} 个节点的结果")
                return {"values": values_update}

            except Exception as e:
                logger.error(f"结果聚合节点执行失败: {e}", exc_info=True)
                return {"values": {"aggregation_error": str(e)}}

        return result_aggregator
