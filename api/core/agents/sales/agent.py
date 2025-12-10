"""
Sales Agent

负责生成最终的销售话术回复。

核心职责:
- 接收 SentimentAgent 提供的策略提示词
- 检索并整合记忆上下文
- 获取并整合助理人设信息
- 生成符合人设和策略的个性化回复
- 自动管理助手回复的存储
"""

from uuid import uuid4

from core.entities import WorkflowExecutionModel
from core.memory import StorageManager
from core.prompts.utils.get_role_prompt import get_role_prompt
from infra.runtimes import CompletionsRequest
from libs.types import Message, MessageParams, InputContent, InputType
from utils import get_current_datetime
from ..base import BaseAgent


class SalesAgent(BaseAgent):
    """
    销售回复生成智能体
    
    专注于执行销售策略，生成最终回复。它利用 SentimentAgent 确定的策略方向，
    结合历史记忆，生成连贯、得体的对话内容。
    """

    def __init__(self):
        super().__init__()

        # 记忆管理
        self.memory_manager = StorageManager()

    def _format_user_context(self, context_list: list[dict]) -> str:
        """格式化用户上下文"""
        if not context_list:
            return ""
            
        # 映射字典
        type_map = {
            "area": "所在地区",
            "job": "职业",
            "wx_nickname": "微信昵称",
            "signature": "个性签名",
            "headImg": "头像URL"
        }
        
        lines = []
        for item in context_list:
            type_val = item.get("type")
            content = item.get("content")
            
            # 跳过空内容
            if not content:
                continue
                
            label = type_map.get(type_val, type_val) # 如果不在映射中，使用原始type
            lines.append(f"- {label}: {content}")
            
        if not lines:
            return ""
            
        return "【客户档案资料】\n" + "\n".join(lines)

    async def process_conversation(self, state: WorkflowExecutionModel) -> dict:
        """
        处理对话状态，生成销售回复
        
        工作流程：
        1. 获取 SentimentAgent 确定的策略提示词
        2. 检索记忆上下文（长期+短期）
        3. 构建包含上下文的 LLM 提示词
        4. 生成回复
        5. 存储回复并更新状态
        
        Args:
            state: 当前工作流执行状态
            
        Returns:
            dict: 状态更新增量，包含 sales_response
        """
        start_time = get_current_datetime()

        try:
            self.logger.info("=== Sales Agent 开始处理 ===")

            customer_input = state.input
            tenant_id = state.tenant_id
            thread_id = str(state.thread_id)
            assistant_id = state.assistant_id
    
            matched_prompt = state.matched_prompt
            current_total_tokens = state.total_tokens

            if not matched_prompt:
                matched_prompt = {}

            # 获取助理人设信息
            role_prompt = None
            if assistant_id:
                try:
                    role_prompt = await get_role_prompt(assistant_id, use_cache=True)
                    self.logger.info(f"已获取助理人设信息: {role_prompt.content[:100]}...")
                except Exception as e:
                    self.logger.warning(f"获取助理人设信息失败: {e}")
                    role_prompt = None

            self.logger.info(f"sales agent 匹配提示词: {matched_prompt.get('matched_key', 'unknown')}")

            # 解析用户输入为文本
            user_text, _ = self._parse_input(customer_input)
            short_term_messages, long_term_memories = await self.memory_manager.retrieve_context(
                tenant_id=tenant_id,
                thread_id=thread_id,
                query_text=user_text,
            )
            self.logger.info(f"记忆检索完成 - 短期: {len(short_term_messages)} 条, 长期: {len(long_term_memories)} 条")

            # 按照设计模式，用户上下文通过memory manager获取
            # 目前用户档案信息暂未集成到工作流中
            formatted_context = ""

            # 生成个性化回复（基于匹配的提示词 + 人设 + 记忆 + 用户上下文）
            sales_response, token_info = await self.__generate_final_response(
                user_text, matched_prompt, role_prompt, short_term_messages, long_term_memories, formatted_context
            )

            # 存储助手回复到记忆
            if sales_response and tenant_id and thread_id:
                try:
                    await self.memory_manager.save_assistant_message(
                        tenant_id=tenant_id,
                        thread_id=thread_id,
                        message=sales_response,
                    )
                    self.logger.debug("助手回复已保存到记忆")
                except Exception as e:
                    self.logger.error(f"保存助手回复失败: {e}")

            # 更新状态 - 返回增量字典
            
            token_usage = {
                "input_tokens": token_info.get("input_tokens", 0),
                "output_tokens": token_info.get("output_tokens", 0),
                "total_tokens": token_info.get("total_tokens", 0)
            }

            agent_data = {
                "agent_type": "sales",
                "sales_response": sales_response,
                "response": sales_response,  # 标准化的响应字段
                "token_usage": token_usage,  # 标准化的token信息
                "tokens_used": token_usage["total_tokens"],  # 向后兼容
                "timestamp": get_current_datetime(),
                "response_length": len(sales_response)
            }

            processing_time = (get_current_datetime() - start_time).total_seconds()
            self.logger.info(f"最终回复生成完成: 耗时{processing_time:.2f}s, 长度={len(sales_response)}, tokens={token_info.get('tokens_used', 0)}")
            self.logger.info("=== Sales Agent 处理完成 ===")

            return {
                "output": sales_response, # 更新最终输出
                "input_tokens": token_usage["input_tokens"],
                "output_tokens": token_usage["output_tokens"],
                "total_tokens": current_total_tokens + token_usage["total_tokens"],
                "values": {"agent_responses": {self.agent_id: agent_data}},
                "active_agents": [self.agent_id]
            }

        except Exception as e:
            self.logger.error(f"销售代理处理失败: {e}", exc_info=True)
            raise e


    async def __generate_final_response(
        self,
        customer_input: str,
        matched_prompt: dict,
        role_prompt: Message,
        short_term_messages: list,
        long_term_memories: list,
        formatted_context: str = ""
    ) -> tuple[str, dict]:
        """
        基于匹配提示词、人设信息和记忆生成回复

        Args:
            customer_input: 客户输入
            matched_prompt: SentimentAgent 匹配的提示词
            role_prompt: 助理人设提示词（从get_role_prompt获取）
            short_term_messages: 短期记忆消息列表
            long_term_memories: 长期记忆摘要列表
            formatted_context: 格式化后的用户上下文字符串

        Returns:
            tuple: (回复内容, token信息)
        """
        try:
            # 1. 构建基础系统提示（整合人设、匹配提示词等）
            base_system_prompt = matched_prompt.get("system_prompt", "你是一个人。")
            tone = matched_prompt.get("tone", "专业、友好")
            strategy = matched_prompt.get("strategy", "标准服务")

            # 2. 整合人设信息、长期记忆和用户上下文到系统提示
            enhanced_system_prompt = self._build_system_prompt_with_memory(
                base_system_prompt, tone, strategy, role_prompt, long_term_memories, formatted_context
            )

            # 3. 构建消息列表（直接使用记忆消息）
            llm_messages = [Message(role="system", content=enhanced_system_prompt)]
            llm_messages.extend(short_term_messages)  # 直接添加短期记忆消息
            llm_messages.append(Message(role="user", content=customer_input))

            # 4. 调用 LLM
            request = CompletionsRequest(
                id=uuid4(),
                provider="openrouter",
                model="openai/gpt-5-mini",
                temperature=0.7,  # 适度创造性
                messages=llm_messages
            )

            llm_response = await self.invoke_llm(request)

            # 5. 提取 token 信息
            token_info = self._extract_token_info(llm_response)

            # 6. 返回响应
            if llm_response and llm_response.content:
                response_content = str(llm_response.content).strip()
                self.logger.debug(f"LLM 回复预览: {response_content[:100]}...")
                return response_content, token_info
            else:
                return self._get_fallback_response(matched_prompt), {}

        except Exception as e:
            self.logger.error(f"回复生成失败: {e}")
            return self._get_fallback_response(matched_prompt), {"tokens_used": 0, "error": str(e)}

    def _build_system_prompt_with_memory(
        self, base_prompt: str, tone: str, strategy: str, role_prompt: Message, summaries: list, formatted_context: str = ""
    ) -> str:
        """
        构建增强的系统提示词

        Args:
            base_prompt: 基础系统提示词
            tone: 语气要求
            strategy: 策略要求
            role_prompt: 助理人设提示词
            summaries: 长期记忆摘要列表
            formatted_context: 格式化后的用户上下文

        Returns:
            str: 增强后的系统提示词
        """
        # 构建基础提示，优先使用人设信息
        if role_prompt and role_prompt.content:
            # 如果有人设信息，将其作为核心提示，然后融合其他要求
            enhanced_prompt = f"""
{role_prompt.content}

【当前对话策略】
{base_prompt}

【语气要求】{tone}
【策略要求】{strategy}

【回复要求】
- 用中文回复，语言自然流畅
- 控制在150字以内，每句话最多只能存在2个逗号。句号用\n换行号替代
- 体现个性化，避免模板化回复
- 根据客户历史适度调整策略
- 始终保持上述人设特征进行对话
            """.strip()
        else:
            # 如果没有人设信息，使用原有逻辑
            enhanced_prompt = f"""
{base_prompt}

【语气要求】{tone}
【策略要求】{strategy}

【回复要求】
- 用中文回复，语言自然流畅
- 控制在150字以内
- 体现个性化，避免模板化回复
- 根据客户历史适度调整策略
            """.strip()

        # 添加用户档案（如果有）
        if formatted_context:
            enhanced_prompt += f"\n\n{formatted_context}"

        # 添加长期记忆（如果有）
        if summaries:
            memory_lines = []
            for idx, summary in enumerate(summaries[:3], 1):  # 最多3条摘要
                content = summary.get("content") or ""
                tags = summary.get("tags") or []
                tag_display = (
                    f" (标签: {', '.join(str(tag) for tag in tags)})"
                    if tags
                    else ""
                )
                memory_lines.append(f"{idx}. {content[:100]}{tag_display}")  # 限制长度

            enhanced_prompt += f"\n\n【客户历史背景】\n" + "\n".join(memory_lines)

        return enhanced_prompt

    def _extract_token_info(self, llm_response) -> dict:
        """提取 token 使用信息"""
        try:
            token_usage = getattr(llm_response, "usage", {}) or {}
            input_tokens = token_usage.get("input_tokens", 0)
            output_tokens = token_usage.get("output_tokens", 0)
            total_tokens = token_usage.get("total_tokens", input_tokens + output_tokens)
            
            return {
                "tokens_used": total_tokens,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens
            }
        except Exception as e:
            self.logger.warning(f"Token 信息提取失败: {e}")

        return {"tokens_used": 0, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    def _get_fallback_response(self, matched_prompt: dict) -> str:
        """获取兜底回复"""
        tone = matched_prompt.get("tone", "专业、友好")

        if "温和" in tone or "关怀" in tone:
            return "我理解您的感受"
        elif "积极" in tone or "热情" in tone:
            return "太好了！"
        else:
            return "感谢您的咨询。"

    def _parse_input(self, messages: MessageParams) -> tuple[str, set[InputType]]:
        """
        解析输入消息列表，提取文本内容和检测内容类型

        Args:
            messages: 消息列表 (MessageParams)

        Returns:
            tuple[str, set[InputType]]: (合并后的文本内容, 检测到的输入类型集合)
        """
        parts: list[str] = []
        types: set[InputType] = set()

        for message in messages:
            content = message.content
            if isinstance(content, str):
                parts.append(f"{message.role}: {content}")
                types.add(InputType.TEXT)
            else:
                for item in content:
                    if isinstance(item, InputContent):
                        parts.append(f"{message.role}: {item.content}")
                        types.add(item.type)

        return "\n".join(parts), types

