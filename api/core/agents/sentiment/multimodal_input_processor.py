"""
多模态输入处理器 - 简化版本

直接使用LLM的多模态能力处理不同类型的输入，
将复杂的预处理逻辑简化为直接的LLM调用。

核心功能:
- 支持 Sequence[InputContent] 多模态输入
- 直接利用LLM原生多模态能力
- 将多模态内容转换为纯文字
- 提供简洁的处理结果
"""

from collections.abc import Sequence
from typing import Any
from uuid import uuid4

from libs.types import InputContentParams, InputContent, InputType, Message, MessageParams
from infra.runtimes import LLMClient, CompletionsRequest
from utils import LoggerMixin


class MultimodalInputProcessor(LoggerMixin):
    """
    简化的多模态输入处理器

    直接使用LLM的多模态能力，避免复杂的预处理管道。
    """

    def __init__(self, tenant_id: str = None):
        super().__init__()
        self.tenant_id = tenant_id
        self.llm_client = LLMClient()

    async def process_input(self, customer_input: MessageParams) -> tuple[str, dict[str, Any]]:
        """
        处理多模态输入消息列表

        参数:
            customer_input: 消息列表 (MessageParams)

        返回:
            tuple[str, dict[str, Any]]: (处理后的纯文字, 多模态上下文)
        """
        # 提取所有用户消息的内容
        all_contents: list[InputContentParams] = []
        for message in customer_input:
            if message.role != "user":
                continue
            all_contents.append(message.content)

        if not all_contents:
            return "", {
                "type": "empty",
                "modalities": [],
                "item_count": 0
            }

        # 处理每个内容项
        combined_texts: list[str] = []
        all_modalities: set = set()
        total_items = 0

        for content in all_contents:
            if isinstance(content, str):
                combined_texts.append(content)
                all_modalities.add("text")
                total_items += 1
            else:
                # Sequence[InputContent]
                text, context = await self._extract_text_from_multimodal(content)
                combined_texts.append(text)
                all_modalities.update(context.get("modalities", []))
                total_items += context.get("item_count", 0)

        return " ".join(combined_texts), {
            "type": "multimodal" if len(all_modalities) > 1 else "text",
            "modalities": list(all_modalities),
            "item_count": total_items
        }

    async def _extract_text_from_multimodal(self, input_sequence: Sequence[InputContent]) -> tuple[str, dict[str, Any]]:
        """
        从多模态输入序列中提取文字

        使用LLM直接理解多模态内容并转换为文字描述
        """
        try:
            # 构建用于LLM处理的消息
            llm_messages = []
            modalities = set()

            for item in input_sequence:
                if isinstance(item, dict):
                    content_type = item.get("type", InputType.TEXT)
                    content = item.get("content", "")
                else:
                    # 如果是InputContent对象
                    content_type = getattr(item, "type", InputType.TEXT)
                    content = getattr(item, "content", "")

                modalities.add(content_type)

                if content_type == InputType.TEXT:
                    llm_messages.append({"type": "text", "text": content})
                elif content_type == InputType.IMAGE:
                    llm_messages.append({
                        "type": "image_url",
                        "image_url": {"url": content}
                    })
                elif content_type == InputType.AUDIO:
                    # 对于音频，我们先提供占位符，后续可以集成Whisper
                    llm_messages.append({
                        "type": "text",
                        "text": f"[音频内容: {content}]"
                    })
                else:
                    # 其他类型转为文本描述
                    llm_messages.append({
                        "type": "text",
                        "text": f"[{content_type}类型内容: {content}]"
                    })

            # 如果包含多模态内容，使用LLM提取文字
            if len(modalities) > 1 or InputType.IMAGE in modalities:
                extracted_text = await self._llm_extract_text(llm_messages)
            else:
                # 如果只是纯文本，直接拼接
                extracted_text = " ".join(
                    msg["text"] for msg in llm_messages
                    if msg["type"] == "text"
                )

            context = {
                "type": "multimodal",
                "modalities": list(modalities),
                "item_count": len(input_sequence),
                "processing_method": "llm_extraction"
            }

            return extracted_text or "无有效内容", context

        except Exception as e:
            self.logger.error(f"多模态处理失败: {e}")
            # 降级处理：尝试提取所有文本内容
            fallback_text = self._extract_fallback_text(input_sequence)
            return fallback_text, {
                "type": "fallback",
                "modalities": ["text"],
                "item_count": len(input_sequence),
                "error": str(e)
            }

    async def _llm_extract_text(self, messages: list[dict[str, Any]]) -> str:
        """
        使用LLM提取多模态内容的文字描述

        使用LLM直接理解多模态内容并转换为文字描述
        """
        try:
            # 1. 转换回 InputContent 列表
            content_list = []
            for msg in messages:
                if msg["type"] == "text":
                    content_list.append(InputContent(type=InputType.TEXT, content=msg["text"]))
                elif msg["type"] == "image_url":
                    # 确保提取 URL 字符串
                    url_data = msg["image_url"]
                    url = url_data["url"] if isinstance(url_data, dict) else url_data
                    content_list.append(InputContent(type=InputType.IMAGE, content=url))
            
            if not content_list:
                return ""

            # 2. 构建系统提示词
            system_prompt = (
                "你是一个专业的视觉分析助手。请详细描述用户发送的内容。"
                "如果是图片，请描述图片中的主体、场景、细节以及可能包含的情感或文字信息。"
                "如果是文本，请保持原意。"
                "如果是图文混合，请综合理解并生成连贯的描述。"
                "输出应为纯文本段落，不要包含Markdown格式或其他无关内容。"
            )

            # 3. 构建 LLM 请求消息
            llm_messages = [
                Message(role="system", content=system_prompt),
                Message(role="user", content=content_list)
            ]

            # 4. 发送请求
            request = CompletionsRequest(
                id=uuid4(),
                model="openai/gpt-4o",  # 使用支持视觉的模型
                provider="openrouter",
                temperature=0.5,
                messages=llm_messages
            )

            self.logger.info(f"调用多模态LLM进行图片分析: {len(content_list)}个内容项")
            response = await self.llm_client.completions(request)
            
            # 5. 处理响应
            content = response.content
            result_text = content.get("content", "") if isinstance(content, dict) else str(content)
            
            self.logger.info(f"图片分析完成，描述长度: {len(result_text)}")
            return result_text

        except Exception as e:
            self.logger.error(f"LLM提取多模态文字失败: {e}", exc_info=True)
            # 降级处理：简单拼接
            text_parts = []
            for msg in messages:
                if msg["type"] == "text":
                    text_parts.append(msg["text"])
                elif msg["type"] == "image_url":
                    url = msg["image_url"]["url"]
                    text_parts.append(f"[图片: {url}]")
            return " ".join(text_parts)

    def _extract_fallback_text(self, input_sequence: Sequence[InputContent]) -> str:
        """降级文本提取"""
        text_parts = []
        for item in input_sequence:
            if isinstance(item, dict):
                if item.get("type") == InputType.TEXT:
                    text_parts.append(item.get("content", ""))
            else:
                # InputContent对象
                if getattr(item, "type", None) == InputType.TEXT:
                    text_parts.append(getattr(item, "content", ""))

        return " ".join(filter(None, text_parts)) or "无文本内容"
