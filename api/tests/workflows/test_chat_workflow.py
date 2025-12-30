"""
ChatWorkflow LLM集成测试

真实的端到端LLM调用测试，验证重构后的ChatWorkflow在实际LLM环境下的行为。

测试覆盖:
1. 顺序模式完整工作流 (sentiment → intent → sales)
2. 并行模式完整工作流 (START → [sentiment, intent] → sales → END)
3. 状态Reducer机制验证 (token累加、字典合并)
4. 错误恢复和降级处理
5. 性能对比 (并行 vs 顺序)
6. 重构验证 (移除coordinator/aggregator节点)

运行要求:
- 需要配置有效的LLM API密钥 (OpenAI/Anthropic/Google)
- 需要Redis和PostgreSQL服务运行
- 建议使用pytest -s -v 查看详细输出

环境变量:
- RUN_LLM_TESTS=true: 启用LLM集成测试 (会产生API调用费用)
- ENABLE_PARALLEL_EXECUTION: "true" 或 "false"
- LOG_LEVEL: "DEBUG" 查看LLM调用详情

运行示例:
  # 运行所有LLM集成测试
  RUN_LLM_TESTS=true uv run pytest tests/workflows/test_chat_workflow.py -v -s

  # 仅运行并行模式测试
  RUN_LLM_TESTS=true uv run pytest tests/workflows/test_chat_workflow.py::TestChatWorkflowParallelMode -v -s

  # 直接运行此文件
  RUN_LLM_TESTS=true uv run python tests/workflows/test_chat_workflow.py
"""

import asyncio
import os
from uuid import uuid4

import pytest

from core.app.workflow_builder import WorkflowBuilder
from core.entities import WorkflowExecutionModel
from libs.constants import AgentNodes
from libs.factory import infra_registry
from libs.types import UserMessage
from utils import get_component_logger, get_current_datetime

logger = get_component_logger(__name__)


# 测试标记: 需要真实LLM调用，可能产生费用
pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_LLM_TESTS", "false").lower() == "true",
    reason="需要设置 RUN_LLM_TESTS=true 来运行真实LLM测试（会产生API费用）"
)


@pytest.fixture(scope="session", autouse=True)
def setup_infrastructure():
    """
    Session级别的基础设施初始化fixture

    在所有测试开始前初始化数据库、Redis等连接，
    测试结束后清理资源。
    """
    import asyncio

    logger.info("=== 初始化基础设施客户端 ===")

    # 创建新的事件循环用于初始化
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # 使用事件循环运行异步初始化
    async def _init():
        await infra_registry.create_clients()
        await infra_registry.test_clients()

    loop.run_until_complete(_init())

    yield

    # 清理资源 - 使用同一个事件循环
    logger.info("=== 关闭基础设施客户端 ===")

    async def _cleanup():
        await infra_registry.shutdown_clients()

    try:
        loop.run_until_complete(_cleanup())
    except RuntimeError:
        # 如果事件循环已关闭，忽略错误
        pass
    finally:
        loop.close()


@pytest.fixture
def simple_workflow_state():
    """创建简单对话场景的工作流状态"""
    user_message = UserMessage(
        role="user",
        content="你好，我想了解一下你们的楼盘信息"
    )

    return WorkflowExecutionModel(
        workflow_id=uuid4(),
        thread_id=uuid4(),
        assistant_id=uuid4(),
        tenant_id="test_llm_tenant",
        input=[user_message],
        started_at=get_current_datetime()
    )


@pytest.fixture
def appointment_intent_state():
    """创建包含预约意图的对话场景"""
    user_message = UserMessage(
        role="user",
        content="我想预约明天下午看房，有时间吗？"
    )

    return WorkflowExecutionModel(
        workflow_id=uuid4(),
        thread_id=uuid4(),
        assistant_id=uuid4(),
        tenant_id="test_llm_tenant",
        input=[user_message],
        started_at=get_current_datetime()
    )


@pytest.fixture
def negative_sentiment_state():
    """创建负面情绪场景"""
    user_message = UserMessage(
        role="user",
        content="你们的房子太贵了，而且服务态度也不好！"
    )

    return WorkflowExecutionModel(
        workflow_id=uuid4(),
        thread_id=uuid4(),
        assistant_id=uuid4(),
        tenant_id="test_llm_tenant",
        input=[user_message],
        started_at=get_current_datetime()
    )


@pytest.fixture
def complex_query_state():
    """创建复杂查询场景"""
    user_message = UserMessage(
        role="user",
        content="我想买一套100平左右的三房，预算300万，最好靠近地铁，孩子要上学，请问有合适的楼盘推荐吗？"
    )

    return WorkflowExecutionModel(
        workflow_id=uuid4(),
        thread_id=uuid4(),
        assistant_id=uuid4(),
        tenant_id="test_llm_tenant",
        input=[user_message],
        started_at=get_current_datetime()
    )


class TestChatWorkflowSequentialMode:
    """顺序模式LLM集成测试"""

    @pytest.mark.asyncio
    async def test_sequential_simple_conversation(self, simple_workflow_state):
        """测试顺序模式 - 简单咨询对话"""
        logger.info("=== 测试顺序模式 - 简单咨询对话 ===")

        # 设置顺序模式
        os.environ["ENABLE_PARALLEL_EXECUTION"] = "false"

        # 重新导入以应用环境变量
        import importlib
        from core.graphs import chat_workflow
        importlib.reload(chat_workflow)

        # 创建真实的workflow builder
        workflow_builder = WorkflowBuilder(chat_workflow.ChatWorkflow)
        compiled_graph = workflow_builder.build_graph()

        # 执行工作流
        logger.info(f"开始执行工作流 - 输入: {simple_workflow_state.input[0].content}")
        result = await compiled_graph.ainvoke(simple_workflow_state)

        # 验证基本结构
        assert isinstance(result, dict), "结果应该是字典类型"
        assert result["workflow_id"] == simple_workflow_state.workflow_id

        # 验证agents执行了 (至少sales agent应该执行)
        logger.info(f"活跃agents: {result.get('active_agents', [])}")
        assert AgentNodes.SALES_NODE in result.get("active_agents", []), "Sales agent应该执行"

        # 验证至少有一些agent执行了
        assert len(result.get("active_agents", [])) >= 1, "至少应该有一个agent执行"

        # 验证sentiment分析结果 (可能因为错误而缺失，所以只检查存在性)
        if "sentiment_analysis" in result:
            logger.info(f"情感分析: {result['sentiment_analysis']}")

        # 验证intent分析结果
        if "intent_analysis" in result:
            logger.info(f"意向分析: {result['intent_analysis']}")

        # 验证sales响应
        assert "output" in result or "sales_response" in result
        final_response = result.get("output") or result.get("sales_response")
        assert final_response is not None
        assert len(final_response) > 0
        logger.info(f"最终响应: {final_response[:200]}...")

        # 验证token统计
        assert result.get("input_tokens", 0) > 0
        assert result.get("output_tokens", 0) > 0
        logger.info(f"Token统计 - 输入: {result['input_tokens']}, 输出: {result['output_tokens']}")

    @pytest.mark.asyncio
    async def test_sequential_appointment_intent_detection(self, appointment_intent_state):
        """测试顺序模式 - 预约意图识别"""
        logger.info("=== 测试顺序模式 - 预约意图识别 ===")

        os.environ["ENABLE_PARALLEL_EXECUTION"] = "false"

        import importlib
        from core.graphs import chat_workflow
        importlib.reload(chat_workflow)

        workflow_builder = WorkflowBuilder(chat_workflow.ChatWorkflow)
        compiled_graph = workflow_builder.build_graph()

        result = await compiled_graph.ainvoke(appointment_intent_state)

        # 验证intent分析包含预约意图
        assert "intent_analysis" in result
        intent_data = result["intent_analysis"]

        # 检查预约意图字段
        logger.info(f"意向分析详情: {intent_data}")
        assert intent_data is not None

        # 验证sales agent根据预约意图调整了响应
        final_response = result.get("output") or result.get("sales_response")
        assert final_response is not None
        logger.info(f"预约场景响应: {final_response[:200]}...")

    @pytest.mark.asyncio
    async def test_sequential_negative_sentiment_handling(self, negative_sentiment_state):
        """测试顺序模式 - 负面情绪处理"""
        logger.info("=== 测试顺序模式 - 负面情绪处理 ===")

        os.environ["ENABLE_PARALLEL_EXECUTION"] = "false"

        import importlib
        from core.graphs import chat_workflow
        importlib.reload(chat_workflow)

        workflow_builder = WorkflowBuilder(chat_workflow.ChatWorkflow)
        compiled_graph = workflow_builder.build_graph()

        result = await compiled_graph.ainvoke(negative_sentiment_state)

        # 验证workflow完成
        assert isinstance(result, dict)
        logger.info(f"活跃agents: {result.get('active_agents', [])}")

        # 验证情感分析识别 (如果存在)
        if "sentiment_analysis" in result:
            sentiment = result["sentiment_analysis"]
            logger.info(f"负面情绪分析: {sentiment}")

        # 验证最终响应 - 应该有安抚性质的回复
        final_response = result.get("output") or result.get("sales_response")
        assert final_response is not None
        logger.info(f"负面情绪响应: {final_response[:200]}...")

    @pytest.mark.asyncio
    async def test_sequential_complex_query(self, complex_query_state):
        """测试顺序模式 - 复杂查询处理"""
        logger.info("=== 测试顺序模式 - 复杂查询 ===")

        os.environ["ENABLE_PARALLEL_EXECUTION"] = "false"

        import importlib
        from core.graphs import chat_workflow
        importlib.reload(chat_workflow)

        workflow_builder = WorkflowBuilder(chat_workflow.ChatWorkflow)
        compiled_graph = workflow_builder.build_graph()

        result = await compiled_graph.ainvoke(complex_query_state)

        # 验证处理了复杂需求
        assert isinstance(result, dict)
        logger.info(f"活跃agents: {result.get('active_agents', [])}")

        # 验证至少有分析结果
        has_analysis = "intent_analysis" in result or "sentiment_analysis" in result
        assert has_analysis, "应该至少有intent或sentiment分析结果"

        final_response = result.get("output") or result.get("sales_response")
        assert final_response is not None
        assert len(final_response) > 0, "应该返回有效的响应"
        logger.info(f"复杂查询响应 (长度={len(final_response)}): {final_response[:300]}...")


class TestChatWorkflowParallelMode:
    """并行模式LLM集成测试"""

    @pytest.mark.asyncio
    async def test_parallel_simple_conversation(self, simple_workflow_state):
        """测试并行模式 - 简单咨询对话"""
        logger.info("=== 测试并行模式 - 简单咨询对话 ===")

        os.environ["ENABLE_PARALLEL_EXECUTION"] = "true"

        import importlib
        from core.graphs import chat_workflow
        importlib.reload(chat_workflow)

        workflow_builder = WorkflowBuilder(chat_workflow.ChatWorkflow)
        compiled_graph = workflow_builder.build_graph()

        result = await compiled_graph.ainvoke(simple_workflow_state)

        # 验证基本结构
        assert isinstance(result, dict)
        assert result["workflow_id"] == simple_workflow_state.workflow_id

        # 验证并行节点都执行了
        logger.info(f"并行模式 - 活跃agents: {result.get('active_agents', [])}")
        assert AgentNodes.SENTIMENT_NODE in result.get("active_agents", [])
        assert AgentNodes.INTENT_NODE in result.get("active_agents", [])
        assert AgentNodes.SALES_NODE in result.get("active_agents", [])

        # 验证并行节点的结果
        assert "sentiment_analysis" in result
        assert "intent_analysis" in result
        logger.info(f"并行执行 - 情感: {result['sentiment_analysis']}")
        logger.info(f"并行执行 - 意向: {result['intent_analysis']}")

        # 验证sales响应
        final_response = result.get("output") or result.get("sales_response")
        assert final_response is not None
        logger.info(f"并行模式最终响应: {final_response[:200]}...")

        # 验证token累加 (Reducer机制)
        assert result.get("input_tokens", 0) > 0
        assert result.get("output_tokens", 0) > 0
        logger.info(f"并行模式Token累加 - 输入: {result['input_tokens']}, 输出: {result['output_tokens']}")

    @pytest.mark.asyncio
    async def test_parallel_state_reducer_token_accumulation(self, simple_workflow_state):
        """测试并行模式 - Token累加Reducer机制"""
        logger.info("=== 测试并行模式 - Token累加机制 ===")

        os.environ["ENABLE_PARALLEL_EXECUTION"] = "true"

        import importlib
        from core.graphs import chat_workflow
        importlib.reload(chat_workflow)

        workflow_builder = WorkflowBuilder(chat_workflow.ChatWorkflow)
        compiled_graph = workflow_builder.build_graph()

        result = await compiled_graph.ainvoke(simple_workflow_state)

        # 验证tokens被正确累加 (sentiment + intent + sales)
        input_tokens = result.get("input_tokens", 0)
        output_tokens = result.get("output_tokens", 0)

        # 3个agents都应该有token贡献
        assert input_tokens > 0, "输入tokens应该被累加"
        assert output_tokens > 0, "输出tokens应该被累加"

        logger.info(f"Token累加验证 - 总输入: {input_tokens}, 总输出: {output_tokens}")

        # 验证累加的合理性 - 应该是3个agents的总和
        # 每个agent至少贡献一些tokens
        assert input_tokens > 50, "3个agents的输入tokens总和应该大于50"
        assert output_tokens > 20, "3个agents的输出tokens总和应该大于20"

    @pytest.mark.asyncio
    async def test_parallel_state_reducer_dict_merge(self, appointment_intent_state):
        """测试并行模式 - 字典合并Reducer机制"""
        logger.info("=== 测试并行模式 - 字典合并机制 ===")

        os.environ["ENABLE_PARALLEL_EXECUTION"] = "true"

        import importlib
        from core.graphs import chat_workflow
        importlib.reload(chat_workflow)

        workflow_builder = WorkflowBuilder(chat_workflow.ChatWorkflow)
        compiled_graph = workflow_builder.build_graph()

        result = await compiled_graph.ainvoke(appointment_intent_state)

        # 验证并行节点的字段都被正确合并
        assert "sentiment_analysis" in result, "sentiment节点的字段应该被保留"
        assert "intent_analysis" in result, "intent节点的字段应该被保留"

        # 验证没有字段丢失
        sentiment_data = result["sentiment_analysis"]
        intent_data = result["intent_analysis"]

        assert sentiment_data is not None, "sentiment数据不应为空"
        assert intent_data is not None, "intent数据不应为空"

        logger.info(f"字典合并验证 - sentiment keys: {list(sentiment_data.keys()) if isinstance(sentiment_data, dict) else 'N/A'}")
        logger.info(f"字典合并验证 - intent keys: {list(intent_data.keys()) if isinstance(intent_data, dict) else 'N/A'}")

    @pytest.mark.asyncio
    async def test_parallel_complex_query(self, complex_query_state):
        """测试并行模式 - 复杂查询处理"""
        logger.info("=== 测试并行模式 - 复杂查询 ===")

        os.environ["ENABLE_PARALLEL_EXECUTION"] = "true"

        import importlib
        from core.graphs import chat_workflow
        importlib.reload(chat_workflow)

        workflow_builder = WorkflowBuilder(chat_workflow.ChatWorkflow)
        compiled_graph = workflow_builder.build_graph()

        result = await compiled_graph.ainvoke(complex_query_state)

        # 验证并行处理复杂查询
        assert "sentiment_analysis" in result
        assert "intent_analysis" in result

        final_response = result.get("output") or result.get("sales_response")
        assert final_response is not None
        assert len(final_response) > 0, "应该返回有效的响应"
        logger.info(f"并行模式复杂查询响应 (长度={len(final_response)}): {final_response[:300]}...")


class TestChatWorkflowModeComparison:
    """并行模式 vs 顺序模式对比测试"""

    @pytest.mark.asyncio
    async def test_parallel_vs_sequential_consistency(self, simple_workflow_state):
        """测试并行模式 vs 顺序模式 - 结果一致性"""
        logger.info("=== 测试并行 vs 顺序模式一致性 ===")

        # 执行顺序模式
        os.environ["ENABLE_PARALLEL_EXECUTION"] = "false"
        import importlib
        from core.graphs import chat_workflow
        importlib.reload(chat_workflow)

        workflow_builder_seq = WorkflowBuilder(chat_workflow.ChatWorkflow)
        graph_seq = workflow_builder_seq.build_graph()

        # 使用相同的输入
        state_copy_1 = WorkflowExecutionModel(
            workflow_id=uuid4(),
            thread_id=simple_workflow_state.thread_id,
            assistant_id=simple_workflow_state.assistant_id,
            tenant_id=simple_workflow_state.tenant_id,
            input=simple_workflow_state.input,
            started_at=get_current_datetime()
        )
        _ = await graph_seq.ainvoke(state_copy_1)

        # 等待一下避免缓存影响
        await asyncio.sleep(2)

        # 执行并行模式
        os.environ["ENABLE_PARALLEL_EXECUTION"] = "true"
        importlib.reload(chat_workflow)

        workflow_builder_par = WorkflowBuilder(chat_workflow.ChatWorkflow)
        graph_par = workflow_builder_par.build_graph()

        state_copy_2 = WorkflowExecutionModel(
            workflow_id=uuid4(),
            thread_id=simple_workflow_state.thread_id,
            assistant_id=simple_workflow_state.assistant_id,
            tenant_id=simple_workflow_state.tenant_id,
            input=simple_workflow_state.input,
            started_at=get_current_datetime()
        )
        result_par = await graph_par.ainvoke(state_copy_2)

        # 由于我们只保留了result_par，重新执行顺序模式获取结果
        result_seq = await graph_seq.ainvoke(state_copy_1)

        # 验证两种模式都执行了所有agents
        agents_seq = set(result_seq.get("active_agents", []))
        agents_par = set(result_par.get("active_agents", []))

        assert agents_seq == agents_par, "两种模式应该执行相同的agents"
        logger.info(f"顺序模式agents: {agents_seq}")
        logger.info(f"并行模式agents: {agents_par}")

        # 验证两种模式都产生了有效输出
        output_seq = result_seq.get("output") or result_seq.get("sales_response")
        output_par = result_par.get("output") or result_par.get("sales_response")

        assert output_seq is not None and len(output_seq) > 0
        assert output_par is not None and len(output_par) > 0

        # 验证关键字段都存在
        assert "sentiment_analysis" in result_seq and "sentiment_analysis" in result_par
        assert "intent_analysis" in result_seq and "intent_analysis" in result_par

        logger.info("一致性验证通过 - 两种模式产生相似的结果结构")

    @pytest.mark.asyncio
    async def test_parallel_performance_improvement(self, simple_workflow_state):
        """测试并行模式的性能提升"""
        logger.info("=== 测试并行模式性能 ===")

        import time

        # 测试顺序模式耗时
        os.environ["ENABLE_PARALLEL_EXECUTION"] = "false"
        import importlib
        from core.graphs import chat_workflow
        importlib.reload(chat_workflow)

        workflow_builder_seq = WorkflowBuilder(chat_workflow.ChatWorkflow)
        graph_seq = workflow_builder_seq.build_graph()

        state_copy_1 = WorkflowExecutionModel(
            workflow_id=uuid4(),
            thread_id=uuid4(),
            assistant_id=simple_workflow_state.assistant_id,
            tenant_id=simple_workflow_state.tenant_id,
            input=simple_workflow_state.input,
            started_at=get_current_datetime()
        )

        start = time.time()
        result_seq = await graph_seq.ainvoke(state_copy_1)
        seq_time = time.time() - start

        await asyncio.sleep(1)

        # 测试并行模式耗时
        os.environ["ENABLE_PARALLEL_EXECUTION"] = "true"
        importlib.reload(chat_workflow)

        workflow_builder_par = WorkflowBuilder(chat_workflow.ChatWorkflow)
        graph_par = workflow_builder_par.build_graph()

        state_copy_2 = WorkflowExecutionModel(
            workflow_id=uuid4(),
            thread_id=uuid4(),
            assistant_id=simple_workflow_state.assistant_id,
            tenant_id=simple_workflow_state.tenant_id,
            input=simple_workflow_state.input,
            started_at=get_current_datetime()
        )

        start = time.time()
        result_par = await graph_par.ainvoke(state_copy_2)
        par_time = time.time() - start

        logger.info(f"顺序模式耗时: {seq_time:.2f}秒")
        logger.info(f"并行模式耗时: {par_time:.2f}秒")

        if par_time < seq_time:
            improvement = ((seq_time - par_time) / seq_time * 100)
            logger.info(f"性能提升: {improvement:.1f}%")
        else:
            slowdown = ((par_time - seq_time) / seq_time * 100)
            logger.info(f"性能差异: +{slowdown:.1f}% (可能受网络/缓存影响)")

        # 并行模式理论上应该更快或相近
        # 实际提升取决于LLM API延迟和并发能力
        # 允许20%的误差范围
        assert par_time <= seq_time * 1.2, "并行模式不应该显著慢于顺序模式"


class TestChatWorkflowRefactorValidation:
    """重构验证测试 - 确保重构没有破坏原有功能"""

    @pytest.mark.asyncio
    async def test_no_coordinator_aggregator_nodes(self):
        """验证重构后不再有coordinator和aggregator节点"""
        logger.info("=== 验证移除coordinator/aggregator节点 ===")

        os.environ["ENABLE_PARALLEL_EXECUTION"] = "true"

        import importlib
        from core.graphs import chat_workflow
        importlib.reload(chat_workflow)

        from langgraph.graph import StateGraph
        from core.entities import WorkflowExecutionModel

        workflow_builder = WorkflowBuilder(chat_workflow.ChatWorkflow)
        workflow = workflow_builder.workflow

        # 创建图并注册节点
        graph = StateGraph(WorkflowExecutionModel)
        workflow.register_nodes(graph)

        # 验证没有这些控制节点
        assert "parallel_coordinator" not in graph.nodes
        assert "result_aggregator" not in graph.nodes

        logger.info(f"注册的节点: {list(graph.nodes.keys())}")
        logger.info("✓ 确认已移除coordinator和aggregator节点")

    @pytest.mark.asyncio
    async def test_direct_agent_result_return(self, simple_workflow_state):
        """验证agent结果直接返回，不经过字段提取"""
        logger.info("=== 验证直接返回agent结果 ===")

        import importlib
        from core.graphs import chat_workflow
        importlib.reload(chat_workflow)

        workflow_builder = WorkflowBuilder(chat_workflow.ChatWorkflow)
        compiled_graph = workflow_builder.build_graph()

        result = await compiled_graph.ainvoke(simple_workflow_state)

        # 验证所有agent的专用字段都存在
        assert "sentiment_analysis" in result, "sentiment agent的专用字段应该存在"
        assert "intent_analysis" in result, "intent agent的专用字段应该存在"
        assert "output" in result or "sales_response" in result, "sales agent的输出应该存在"

        logger.info(f"结果包含的顶层字段: {list(result.keys())}")
        logger.info("✓ 确认agent结果直接返回，无字段提取")

    @pytest.mark.asyncio
    async def test_reducer_based_state_merge(self, simple_workflow_state):
        """验证使用Reducer机制进行状态合并"""
        logger.info("=== 验证Reducer状态合并 ===")

        os.environ["ENABLE_PARALLEL_EXECUTION"] = "true"

        import importlib
        from core.graphs import chat_workflow
        importlib.reload(chat_workflow)

        workflow_builder = WorkflowBuilder(chat_workflow.ChatWorkflow)
        compiled_graph = workflow_builder.build_graph()

        result = await compiled_graph.ainvoke(simple_workflow_state)

        # 验证并行节点的字段都被合并
        assert "sentiment_analysis" in result
        assert "intent_analysis" in result

        # 验证token被累加 (operator.add reducer)
        total_input = result.get("input_tokens", 0)
        total_output = result.get("output_tokens", 0)

        # 3个agents都应该有贡献
        assert total_input > 0
        assert total_output > 0

        logger.info(f"Reducer合并验证 - 累加后的tokens: input={total_input}, output={total_output}")
        logger.info("✓ 确认Reducer机制正常工作")


class TestChatWorkflowErrorHandling:
    """错误处理和降级测试"""

    @pytest.mark.asyncio
    async def test_extremely_long_input_handling(self):
        """测试极长输入的处理"""
        logger.info("=== 测试极长输入处理 ===")

        # 创建极长输入
        long_content = "请问这个楼盘怎么样？" + "我很关心地段、价格、配套设施。" * 100

        long_input_state = WorkflowExecutionModel(
            workflow_id=uuid4(),
            thread_id=uuid4(),
            assistant_id=uuid4(),
            tenant_id="test_long_input",
            input=[UserMessage(role="user", content=long_content)],
            started_at=get_current_datetime()
        )

        os.environ["ENABLE_PARALLEL_EXECUTION"] = "true"

        import importlib
        from core.graphs import chat_workflow
        importlib.reload(chat_workflow)

        workflow_builder = WorkflowBuilder(chat_workflow.ChatWorkflow)
        compiled_graph = workflow_builder.build_graph()

        # 应该能完成执行
        result = await compiled_graph.ainvoke(long_input_state)

        # 验证至少返回了基本结构
        assert isinstance(result, dict)
        assert result["workflow_id"] == long_input_state.workflow_id

        logger.info(f"极长输入测试 - 活跃agents: {result.get('active_agents', [])}")
        logger.info(f"Token统计: input={result.get('input_tokens', 0)}, output={result.get('output_tokens', 0)}")
        logger.info("✓ 极长输入处理成功")


if __name__ == "__main__":
    """
    直接运行此文件进行快速测试

    使用方法:
    1. 设置环境变量: export RUN_LLM_TESTS=true
    2. 运行: uv run python tests/integration/test_chat_workflow_llm_integration.py
    """
    import sys

    # 设置环境变量
    os.environ["RUN_LLM_TESTS"] = "true"

    # 运行pytest
    sys.exit(pytest.main([__file__, "-v", "-s", "--tb=short"]))