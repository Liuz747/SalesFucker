#!/usr/bin/env python3
"""
增强版 Sentiment Chat Workflow 测试脚本 - 显示完整调试信息

新增功能:
• 显示每个 agent 接收到的完整提示词
• 显示 LLM 的原始响应和解析结果
• 显示详细的中间处理步骤
• 支持自定义测试用例和批量测试

使用方法:
    # 基础测试
    cd api && python test/workflows/test_sentiment_detailed.py --real-llm --message "你好"

    # 多模态格式测试 (您的原始请求格式)
    cd api && python test/workflows/test_sentiment_detailed.py --real-llm --multimodal

    # 批量测试多个案例 (包含多模态)
    cd api && python test/workflows/test_sentiment_detailed.py --real-llm --batch

    # 显示极详细的调试信息
    cd api && python test/workflows/test_sentiment_detailed.py --real-llm --message "你好" --verbose
"""

import asyncio
import sys
import argparse
import os
import json
from pathlib import Path
from uuid import uuid4
from typing import Dict, Any, List

SCRIPT_DIR = Path(__file__).resolve().parent  # api/test/workflows/
API_DIR = SCRIPT_DIR.parent.parent  # api/
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


def _load_env_file(env_path: Path) -> bool:
    """Load key=value pairs into environment without overriding existing values."""
    if not env_path.exists():
        return False

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key.startswith("#") or key in os.environ:
            continue

        stripped = value.strip().strip('"').strip("'")
        os.environ[key] = stripped

    return True


def load_local_env():
    """Best-effort load of workspace .env files before importing app modules."""
    candidates = [
        API_DIR / ".env.local",
        API_DIR / ".env",
        API_DIR.parent / ".env.local",
        API_DIR.parent / ".env",
    ]
    for env_file in candidates:
        _load_env_file(env_file)


# Load environment configuration once before pulling in app modules
load_local_env()

# 设置必要的环境变量 (在导入任何模块之前)
os.environ.setdefault('CALLBACK_URL', 'http://localhost:8000')
os.environ.setdefault('APP_KEY', 'test_key')


class DetailedLLMInspector:
    """用于捕获和显示 LLM 调用详情的工具类"""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.call_history = []

    def log_llm_call(self, agent_name: str, prompt: str, response: Any, model_info: Dict):
        """记录 LLM 调用信息"""
        call_info = {
            "agent_name": agent_name,
            "model_info": model_info,
            "prompt": prompt,
            "response": response,
            "timestamp": asyncio.get_event_loop().time()
        }
        self.call_history.append(call_info)

    def display_llm_call(self, agent_name: str, prompt: str, response: Any, model_info: Dict):
        """显示单次 LLM 调用的详细信息"""
        print(f"\n{'🔍 LLM 调用详情' : ^50}")
        print("─" * 50)
        print(f"🤖 Agent: {agent_name}")
        print(f"🧠 模型: {model_info.get('provider', 'N/A')} / {model_info.get('model', 'N/A')}")

        # 显示提示词
        print(f"\n📝 发送给 LLM 的提示词:")
        print("┌" + "─" * 48 + "┐")
        # 截断超长提示词
        if len(prompt) > 1000 and not self.verbose:
            truncated_prompt = prompt[:500] + "\n...\n[中间部分已省略]...\n" + prompt[-500:]
            for line in truncated_prompt.split('\n'):
                print(f"│ {line[:46]:<46} │")
        else:
            for line in prompt.split('\n'):
                print(f"│ {line[:46]:<46} │")
        print("└" + "─" * 48 + "┘")

        # 显示响应
        print(f"\n📤 LLM 原始响应:")
        print("┌" + "─" * 48 + "┐")
        response_str = str(response)
        if hasattr(response, 'content'):
            response_str = response.content
        elif hasattr(response, 'text'):
            response_str = response.text
        elif isinstance(response, dict):
            response_str = json.dumps(response, ensure_ascii=False, indent=2)

        # 截断超长响应
        if len(response_str) > 800 and not self.verbose:
            truncated_response = response_str[:400] + "\n...\n[中间部分已省略]...\n" + response_str[-400:]
            for line in truncated_response.split('\n'):
                print(f"│ {line[:46]:<46} │")
        else:
            for line in response_str.split('\n'):
                print(f"│ {line[:46]:<46} │")
        print("└" + "─" * 48 + "┘")


class EnhancedSentimentAgent:
    """增强的情感分析 Agent，带有详细调试信息"""

    def __init__(self, original_agent, inspector: DetailedLLMInspector):
        self.original_agent = original_agent
        self.inspector = inspector
        self.agent_id = getattr(original_agent, 'agent_id', 'sentiment_analysis')
        self.name = "EnhancedSentimentAgent"

        # 拦截原始的 invoke_llm 方法
        original_invoke_llm = getattr(self.original_agent, 'invoke_llm', None)
        if original_invoke_llm:
            self.original_agent.invoke_llm = self._wrap_invoke_llm(original_invoke_llm, "SentimentAgent")

    async def process_conversation(self, state):
        """包装原始方法，添加调试信息"""
        print(f"\n🎯 【情感分析 Agent】开始处理...")

        # 从 state 中提取客户输入
        customer_input = None
        if hasattr(state, 'input'):
            customer_input = state.input
        elif isinstance(state, dict):
            customer_input = state.get('input') or state.get('customer_input')

        print(f"   📥 接收到的客户输入: {customer_input}")

        # 显示 state 的详细信息
        if isinstance(state, dict):
            print(f"   📊 State 类型: dict, 键: {list(state.keys())}")
        else:
            print(f"   📊 State 类型: {type(state).__name__}")

        # 调用原始处理方法
        result = await self.original_agent.process_conversation(state)

        print(f"   ✅ 情感分析完成")

        # 显示情感分析结果
        if isinstance(result, dict):
            sentiment_data = result.get('sentiment_analysis')
            intent_data = result.get('intent_analysis')

            if sentiment_data:
                print(f"   💭 情感分析结果:")
                print(f"      • 情感: {sentiment_data.get('sentiment', 'N/A')}")
                print(f"      • 分数: {sentiment_data.get('score', 'N/A')}")
                print(f"      • 情绪: {sentiment_data.get('emotions', 'N/A')}")

            if intent_data:
                print(f"   🎯 意图分析结果:")
                print(f"      • 意图: {intent_data.get('intent', 'N/A')}")
                print(f"      • 类别: {intent_data.get('category', 'N/A')}")

        return result

    def _wrap_invoke_llm(self, original_method, agent_name):
        """包装 invoke_llm 方法以捕获调试信息"""
        async def wrapper(request, *args, **kwargs):
            # 提取提示词信息
            prompt = "N/A"
            model_info = {
                "provider": request.provider if hasattr(request, 'provider') else 'Unknown',
                "model": request.model if hasattr(request, 'model') else 'Unknown'
            }

            if hasattr(request, 'messages') and request.messages:
                # 构建完整的提示词
                prompt_parts = []
                for msg in request.messages:
                    if hasattr(msg, 'role') and hasattr(msg, 'content'):
                        prompt_parts.append(f"[{msg.role}]: {msg.content}")
                    else:
                        prompt_parts.append(str(msg))
                prompt = "\n".join(prompt_parts)

            # 调用原始方法
            response = await original_method(request, *args, **kwargs)

            # 显示调试信息
            self.inspector.display_llm_call(agent_name, prompt, response, model_info)

            return response
        return wrapper


class EnhancedSalesAgent:
    """增强的销售 Agent，带有详细调试信息"""

    def __init__(self, original_agent, inspector: DetailedLLMInspector):
        self.original_agent = original_agent
        self.inspector = inspector
        self.agent_id = getattr(original_agent, 'agent_id', 'sales_agent')
        self.name = "EnhancedSalesAgent"

        # 拦截原始的 invoke_llm 方法（如果存在）
        original_invoke_llm = getattr(self.original_agent, 'invoke_llm', None)
        if original_invoke_llm:
            self.original_agent.invoke_llm = self._wrap_invoke_llm(original_invoke_llm, "SalesAgent")

        # 拦截 response_service 的 generate_response 方法
        if hasattr(self.original_agent, 'response_service'):
            original_generate_response = getattr(self.original_agent.response_service, 'generate_response', None)
            if original_generate_response:
                self.original_agent.response_service.generate_response = self._wrap_generate_response(original_generate_response, "SalesAgent")

    async def process_conversation(self, state):
        """包装原始方法，添加调试信息"""
        print(f"\n🎯 【销售 Agent】开始处理...")

        # 显示接收到的状态信息
        print(f"   📥 接收到的状态信息:")

        # 从 state 中提取客户输入
        customer_input = None
        if hasattr(state, 'input'):
            customer_input = state.input
        elif isinstance(state, dict):
            customer_input = state.get('input') or state.get('customer_input')

        print(f"   📝 用户输入: {customer_input}")

        # 显示接收到的情感分析结果
        sentiment_analysis = None
        intent_analysis = None

        if hasattr(state, 'sentiment_analysis'):
            sentiment_analysis = state.sentiment_analysis
        elif isinstance(state, dict):
            sentiment_analysis = state.get('sentiment_analysis')

        if hasattr(state, 'intent_analysis'):
            intent_analysis = state.intent_analysis
        elif isinstance(state, dict):
            intent_analysis = state.get('intent_analysis')

        if sentiment_analysis:
            print(f"      💭 情感分析:")
            print(f"         • 情感: {sentiment_analysis.get('sentiment', 'N/A')}")
            print(f"         • 分数: {sentiment_analysis.get('score', 'N/A')}")
            print(f"         • 情绪: {sentiment_analysis.get('emotions', 'N/A')}")

        if intent_analysis:
            print(f"      🎯 意图分析:")
            print(f"         • 意图: {intent_analysis.get('intent', 'N/A')}")
            print(f"         • 类别: {intent_analysis.get('category', 'N/A')}")

        # 调用原始处理方法
        result = await self.original_agent.process_conversation(state)

        print(f"   ✅ 销售回复生成完成")

        # 显示生成的回复
        if isinstance(result, dict):
            sales_response = result.get('sales_response') or result.get('output')
            if sales_response:
                print(f"   📤 生成的回复: {sales_response[:100]}...")

        return result

    def _wrap_invoke_llm(self, original_method, agent_name):
        """包装 invoke_llm 方法以捕获调试信息"""
        async def wrapper(request, *args, **kwargs):
            # 提取提示词信息
            prompt = "N/A"
            model_info = {
                "provider": request.provider if hasattr(request, 'provider') else 'Unknown',
                "model": request.model if hasattr(request, 'model') else 'Unknown'
            }

            if hasattr(request, 'messages') and request.messages:
                # 构建完整的提示词
                prompt_parts = []
                for msg in request.messages:
                    if hasattr(msg, 'role') and hasattr(msg, 'content'):
                        prompt_parts.append(f"[{msg.role}]: {msg.content}")
                    else:
                        prompt_parts.append(str(msg))
                prompt = "\n".join(prompt_parts)

            # 调用原始方法
            response = await original_method(request, *args, **kwargs)

            # 显示调试信息
            self.inspector.display_llm_call(agent_name, prompt, response, model_info)

            return response
        return wrapper

    def _wrap_generate_response(self, original_method, agent_name):
        """包装 response_service 的 generate_response 方法以捕获调试信息"""
        async def wrapper(customer_input, response_context, strategy="auto", *args, **kwargs):
            print(f"\n{'🔍 响应生成详情' : ^50}")
            print("─" * 50)
            print(f"🤖 Agent: {agent_name}")
            print(f"📝 客户输入: {customer_input}")
            print(f"🎯 策略: {strategy}")

            # 显示响应上下文
            print(f"\n📊 响应生成上下文:")
            if isinstance(response_context, dict):
                for key, value in response_context.items():
                    if key in ['sentiment_analysis', 'intent_analysis']:
                        print(f"   • {key}: {json.dumps(value, ensure_ascii=False, indent=4)[:200]}...")
                    else:
                        print(f"   • {key}: {str(value)[:100]}...")

            # 调用原始方法
            response = await original_method(customer_input, response_context, strategy, *args, **kwargs)

            print(f"\n📤 生成的最终响应:")
            print(f"   「{response[:200]}...」" if len(response) > 200 else f"   「{response}」")

            return response
        return wrapper


async def test_with_detailed_real_agents(message: str | list, verbose: bool = False):
    """使用增强版真实智能体测试 (显示详细调试信息)

    参数:
        message: 用户输入，可以是字符串或列表格式的多模态内容
        verbose: 是否显示极详细的调试信息
    """
    print("=" * 80)
    print("  增强版 Sentiment Chat Workflow 测试 - 详细调试模式")
    print("=" * 80)

    try:
        # 导入必要模块
        from core.workflows.sentiment_chat_workflow import SentimentChatWorkflow
        from core.app.entities import WorkflowExecutionModel
        from core.agents.sentiment.agent import SentimentAnalysisAgent
        from core.agents.sales.agent import SalesAgent
        from libs.constants import WorkflowConstants
        from langgraph.graph import StateGraph

        print("\n✅ 模块导入成功")

        # 创建调试检查器
        inspector = DetailedLLMInspector(verbose=verbose)

        # 步骤 1: 创建原始智能体
        print("\n" + "─" * 70)
        print("📦 步骤 1: 创建增强版智能体 (含详细调试)")
        print("─" * 70)

        original_sentiment_agent = SentimentAnalysisAgent()
        original_sales_agent = SalesAgent()

        # 创建增强版智能体
        enhanced_agents = {
            WorkflowConstants.SENTIMENT_NODE: EnhancedSentimentAgent(original_sentiment_agent, inspector),
            WorkflowConstants.SALES_NODE: EnhancedSalesAgent(original_sales_agent, inspector),
        }

        print(f"\n✅ 已创建 {len(enhanced_agents)} 个增强版智能体:")
        for agent_id, agent in enhanced_agents.items():
            print(f"   - {agent_id}: {agent.__class__.__name__}")

        # 步骤 2: 构建工作流
        print("\n" + "─" * 70)
        print("🔧 步骤 2: 构建工作流图")
        print("─" * 70)

        workflow = SentimentChatWorkflow(enhanced_agents)
        graph_builder = StateGraph(WorkflowExecutionModel)

        # 注册节点
        workflow._register_nodes(graph_builder)
        workflow._define_edges(graph_builder)
        workflow._set_entry_exit_points(graph_builder)

        # 编译图
        graph = graph_builder.compile()

        print("✅ 工作流图构建成功")
        print(f"   - 节点: {WorkflowConstants.SENTIMENT_NODE} → {WorkflowConstants.SALES_NODE}")

        # 步骤 3: 执行测试
        print(f"\n{'=' * 80}")
        print(f"测试案例 - 详细调试模式")
        print(f"{'=' * 80}")
        # 显示用户输入信息
        if isinstance(message, list):
            print(f"💬 用户输入 (多模态):")
            for i, item in enumerate(message, 1):
                item_type = item.get('type', 'unknown') if isinstance(item, dict) else 'unknown'
                item_content = item.get('content', str(item)) if isinstance(item, dict) else str(item)
                content_preview = item_content[:50] + "..." if len(item_content) > 50 else item_content
                print(f"   {i}. [{item_type}] {content_preview}")
        else:
            print(f"💬 用户输入: {message}")

        # 创建初始状态 - 确保input字段格式正确
        initial_state = WorkflowExecutionModel(
            workflow_id=uuid4(),
            thread_id=uuid4(),
            tenant_id="test_tenant",
            assistant_id=uuid4(),
            input=message,
            timestamp="2024-01-01T00:00:00"
        )

        print(f"\n🚀 开始执行工作流...")
        if isinstance(message, list):
            print(f"   📊 初始状态: 多模态内容 ({len(message)}项)")
        else:
            print(f"   📊 初始状态: {message}")

        # 执行工作流并收集详细结果
        workflow_steps = []
        step_counter = 0

        async for step in graph.astream(initial_state):
            step_counter += 1
            workflow_steps.append(step)

            print(f"\n{'🔄 步骤 ' + str(step_counter) : ^60}")
            print("=" * 60)

            for node_name, node_output in step.items():
                print(f"\n📍 节点 [{node_name}] 执行结果:")
                print("─" * 50)

                # 显示详细的节点输出分析
                if isinstance(node_output, dict):
                    for key, value in node_output.items():
                        if key == 'input':
                            print(f"   📥 输入: {str(value)[:100]}...")
                        elif key == 'sentiment_analysis':
                            print(f"   💭 情感分析: {json.dumps(value, ensure_ascii=False, indent=6)}")
                        elif key == 'intent_analysis':
                            print(f"   🎯 意图分析: {json.dumps(value, ensure_ascii=False, indent=6)}")
                        elif key == 'sales_response':
                            print(f"   🤖 销售回复: {value}")
                        elif key == 'output':
                            print(f"   📤 最终输出: {value}")
                        else:
                            print(f"   🔧 {key}: {str(value)[:100]}...")

        # 获取最终结果
        final_result = {}
        for step in workflow_steps:
            final_result.update(step)

        # 显示最终总结
        print(f"\n{'📊 最终执行总结' : ^80}")
        print("=" * 80)
        print(f"✅ 工作流执行成功")
        print(f"📈 总步骤数: {step_counter}")
        print(f"🔧 最终状态键: {list(final_result.keys())}")

        # 情感分析总结
        sentiment_data = final_result.get('sentiment_analysis')
        if sentiment_data:
            print(f"\n💭 情感分析最终结果:")
            print(f"   • 情感倾向: {sentiment_data.get('sentiment', 'N/A')}")
            print(f"   • 情感分数: {sentiment_data.get('score', 'N/A')}")
            print(f"   • 检测情绪: {sentiment_data.get('emotions', 'N/A')}")
            print(f"   • 满意度: {sentiment_data.get('satisfaction', 'N/A')}")

        # 意图分析总结
        intent_data = final_result.get('intent_analysis')
        if intent_data:
            print(f"\n🎯 意图分析最终结果:")
            print(f"   • 主要意图: {intent_data.get('intent', 'N/A')}")
            print(f"   • 意图类别: {intent_data.get('category', 'N/A')}")
            print(f"   • 决策阶段: {intent_data.get('decision_stage', 'N/A')}")
            print(f"   • 置信度: {intent_data.get('confidence', 'N/A')}")

        # 销售回复总结
        sales_response = final_result.get('sales_response') or final_result.get('output')
        if sales_response:
            print(f"\n🎯 最终 AI 回复:")
            print(f"   「{sales_response}」")

        # LLM 调用历史总结
        if inspector.call_history:
            print(f"\n📈 LLM 调用统计:")
            print(f"   • 总调用次数: {len(inspector.call_history)}")
            for i, call in enumerate(inspector.call_history, 1):
                agent = call['agent_name']
                model = f"{call['model_info']['provider']}/{call['model_info']['model']}"
                print(f"   • 调用 {i}: {agent} → {model}")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def create_multimodal_input(text_content: str, additional_items: list = None) -> list:
    """创建多模态输入格式

    参数:
        text_content: 主要文本内容
        additional_items: 额外的多模态项目列表

    返回:
        list: 多模态内容列表
    """
    content_items = [
        {"type": "text", "content": text_content}
    ]

    if additional_items:
        content_items.extend(additional_items)

    return content_items


async def test_with_multimodal_example(verbose: bool = False):
    """使用多模态格式测试的示例"""
    # 创建多模态测试输入
    multimodal_input = create_multimodal_input("我想了解你们的服务")

    print("=" * 80)
    print("  多模态格式测试示例")
    print("=" * 80)
    print(f"🎯 测试输入格式: {json.dumps(multimodal_input, ensure_ascii=False, indent=2)}")

    await test_with_detailed_real_agents(multimodal_input, verbose)


async def batch_test_multiple_cases(verbose: bool = False):
    """批量测试多个案例（包括多模态格式）"""
    # 测试案例 - 包含字符串和多模态格式
    test_cases = [
        "你好",  # 传统字符串格式
        create_multimodal_input("我想了解美白项目的价格"),  # 多模态格式
        "你们的服务怎么样？",
        create_multimodal_input("我对你们的产品不太满意"),  # 多模态格式
        "能给我推荐一些适合敏感肌的产品吗？",
        # 复杂多模态示例（如果需要的话）
        create_multimodal_input(
            "我对这个产品很感兴趣",
            [{"type": "image_url", "content": "https://example.com/product.jpg"}]
        )
    ]

    print("=" * 80)
    print("  批量测试模式 - 多个测试案例")
    print("=" * 80)

    for i, message in enumerate(test_cases, 1):
        print(f"\n{'🔄 测试案例 ' + str(i) + ' / ' + str(len(test_cases)) : ^80}")
        await test_with_detailed_real_agents(message, verbose)

        if i < len(test_cases):
            print(f"\n{'⏱️  等待 3 秒后进行下一个测试...' : ^80}")
            await asyncio.sleep(3)


async def main():
    """主测试流程"""
    parser = argparse.ArgumentParser(description="增强版 Sentiment Chat Workflow 测试工具")
    parser.add_argument(
        "--real-llm",
        action="store_true",
        help="使用真实 LLM (需要配置 API keys)"
    )
    parser.add_argument(
        "--message",
        type=str,
        default="你好",
        help="指定测试消息"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示极详细的调试信息（包括完整提示词和响应）"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量测试多个预设案例"
    )
    parser.add_argument(
        "--multimodal",
        action="store_true",
        help="使用多模态格式测试您的原始请求"
    )

    args = parser.parse_args()

    if not args.real_llm:
        print("⚠️  此增强版测试脚本仅支持真实 LLM 模式")
        print("    请使用 --real-llm 参数")
        sys.exit(1)

    if args.batch:
        await batch_test_multiple_cases(args.verbose)
    elif args.multimodal:
        await test_with_multimodal_example(args.verbose)
    else:
        await test_with_detailed_real_agents(args.message, args.verbose)


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║     增强版 Sentiment Chat Workflow - 详细调试测试脚本 v1.0        ║
║                                                                  ║
║  新增功能:                                                        ║
║    • 显示完整的 LLM 提示词和响应                                  ║
║    • 显示各个 Agent 的详细处理步骤                                ║
║    • 支持批量测试多个案例                                         ║
║    • 可选的超详细调试模式                                         ║
║                                                                  ║
║  使用示例:                                                        ║
║    python test_sentiment_detailed.py --real-llm --message "你好" ║
║    python test_sentiment_detailed.py --real-llm --multimodal     ║
║    python test_sentiment_detailed.py --real-llm --batch          ║
║    python test_sentiment_detailed.py --real-llm --verbose        ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
""")

    asyncio.run(main())