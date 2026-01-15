"""
摘要服务

负责调用 LLM 对对话窗口进行摘要压缩。
"""

from infra.runtimes import LLMClient, CompletionsRequest
from libs.types import Message
from utils import get_component_logger

logger = get_component_logger(__name__)


class SummarizationService:
    """
    负责调用 LLM 对对话窗口进行摘要压缩。
    """

    def __init__(self, max_length: int = 10000):
        """
        初始化摘要服务

        Args:
            max_length: 摘要最大长度
        """
        self.llm_client = LLMClient()
        self.max_length = max_length

    async def generate_summary(self, text_block: str) -> str:
        """
        生成对话摘要

        Args:
            text_block: 包含对话内容的提示词

        Returns:
            str: 生成的摘要内容
        """

        if not text_block.strip():
            return ""

        clean_block = self._truncate(text_block)

        prompt = self._build_prompt(clean_block)

        try:
            # 构建LLM请求对象
            request = CompletionsRequest(
                id=None,
                model="google/gemini-3-flash-preview",
                provider="openrouter",
                messages=[Message(role="user", content=prompt)],
                max_tokens=3000,
                temperature=0.3  # 使用较低的temperature保证摘要一致性
            )

            # 调用LLM生成摘要
            response = await self.llm_client.completions(request)

            return response.content

        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            raise

    # ---------------------------------------------------------
    # Internal utilities
    # ---------------------------------------------------------
    def _truncate(self, text: str) -> str:
        """避免输入过大，对 textblock 进行字符安全截断。"""
        if len(text) <= self.max_length:
            return text
        return text[: self.max_length] + "\n...[内容已截断]..."

    def _build_prompt(self, content: str) -> str:
        """
        构造高质量摘要 prompt。
        可根据你的实际业务需要进一步增强。
        """

        return (
            "你是一个专业的对话摘要助手。\n"
            "请帮助我从下面的对话内容中生成一个高度概括的摘要。\n"
            "要求：\n"
            "- 清晰地提炼用户意图、事实、目标和上下文\n"
            "- 不要逐句复述\n"
            "- 精炼但保持关键细节\n"
            "- 使用自然的中文\n"
            "\n"
            "以下是对话内容：\n"
            "-------------------------\n"
            f"{content}\n"
            "-------------------------\n"
            "\n"
            "请生成一个结构化、简洁的摘要（建议5-8句）："
        )
