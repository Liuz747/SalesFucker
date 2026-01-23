"""
对话上下文提取模块

该模块从对话历史中提取上下文信息，用于增强RAG检索。

核心功能:
- 从对话历史中提取实体（产品名称、服务类型、价格范围等）
- 识别用户偏好和约束条件
- 跟踪对话主题和转换
- 构建用户画像
"""

from typing import Optional

from libs.types import Message, MessageParams
from utils import get_component_logger

logger = get_component_logger(__name__, "ConversationContext")


class ConversationContext:
    """
    对话上下文提取器

    从对话历史中提取有用的上下文信息，用于增强RAG检索。
    """

    def __init__(self):
        """初始化ConversationContext"""
        pass

    def extract_context(
        self,
        conversation_history: MessageParams,
        current_query: str
    ) -> dict:
        """
        从对话历史中提取上下文

        Args:
            conversation_history: 对话历史消息列表
            current_query: 当前用户查询

        Returns:
            dict: 提取的上下文信息
        """
        try:
            logger.debug(f"提取对话上下文: {len(conversation_history)} 条消息")

            # 提取实体
            entities = self._extract_entities(conversation_history)

            # 识别用户偏好
            preferences = self._extract_preferences(conversation_history)

            # 跟踪对话主题
            topics = self._extract_topics(conversation_history)

            # 识别约束条件
            constraints = self._extract_constraints(conversation_history)

            context = {
                "entities": entities,
                "preferences": preferences,
                "topics": topics,
                "constraints": constraints
            }

            logger.debug(f"上下文提取完成: {len(entities)} 个实体, {len(topics)} 个主题")

            return context

        except Exception as e:
            logger.error(f"上下文提取失败: {e}")
            return {
                "entities": [],
                "preferences": [],
                "topics": [],
                "constraints": {}
            }

    def _extract_entities(self, conversation_history: MessageParams) -> list[dict]:
        """
        从对话中提取实体

        Args:
            conversation_history: 对话历史

        Returns:
            list[dict]: 实体列表
        """
        entities = []

        # 简化实现：提取常见实体类型
        entity_keywords = {
            "product": ["产品", "护肤品", "精华", "面霜", "洗面奶", "化妆品"],
            "service": ["服务", "护理", "治疗", "美容", "按摩", "spa"],
            "price": ["价格", "多少钱", "费用", "优惠", "折扣"],
            "brand": ["品牌", "牌子"],
            "effect": ["效果", "功效", "作用", "美白", "祛痘", "保湿", "抗衰老"]
        }

        for msg in conversation_history:
            if msg.role == "user":
                content = self._message_to_text(msg)

                for entity_type, keywords in entity_keywords.items():
                    for keyword in keywords:
                        if keyword in content:
                            entities.append({
                                "type": entity_type,
                                "value": keyword,
                                "context": content[:50]
                            })

        # 去重
        seen = set()
        unique_entities = []
        for entity in entities:
            key = f"{entity['type']}:{entity['value']}"
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)

        return unique_entities[:10]  # 最多返回10个实体

    def _extract_preferences(self, conversation_history: MessageParams) -> list[str]:
        """
        识别用户偏好

        Args:
            conversation_history: 对话历史

        Returns:
            list[str]: 用户偏好列表
        """
        preferences = []

        # 偏好关键词
        preference_keywords = {
            "喜欢": "positive",
            "想要": "positive",
            "需要": "positive",
            "不喜欢": "negative",
            "不想要": "negative",
            "不需要": "negative",
            "适合": "positive",
            "推荐": "positive"
        }

        for msg in conversation_history:
            if msg.role == "user":
                content = self._message_to_text(msg)

                for keyword, sentiment in preference_keywords.items():
                    if keyword in content:
                        # 提取偏好描述
                        start_idx = content.find(keyword)
                        preference_text = content[start_idx:start_idx + 30]
                        preferences.append(f"{sentiment}:{preference_text}")

        return preferences[:5]  # 最多返回5个偏好

    def _extract_topics(self, conversation_history: MessageParams) -> list[str]:
        """
        跟踪对话主题

        Args:
            conversation_history: 对话历史

        Returns:
            list[str]: 对话主题列表
        """
        topics = []

        # 主题关键词
        topic_keywords = [
            "护肤", "美容", "化妆", "保养", "治疗",
            "产品", "服务", "价格", "预约", "咨询"
        ]

        for msg in conversation_history:
            if msg.role == "user":
                content = self._message_to_text(msg)

                for topic in topic_keywords:
                    if topic in content and topic not in topics:
                        topics.append(topic)

        return topics

    def _extract_constraints(self, conversation_history: MessageParams) -> dict:
        """
        识别约束条件

        Args:
            conversation_history: 对话历史

        Returns:
            dict: 约束条件字典
        """
        constraints = {}

        # 价格约束
        price_keywords = ["预算", "价格", "多少钱", "便宜", "贵"]
        for msg in conversation_history:
            if msg.role == "user":
                content = self._message_to_text(msg)

                for keyword in price_keywords:
                    if keyword in content:
                        constraints["price_sensitive"] = True
                        break

        # 时间约束
        time_keywords = ["急", "马上", "立即", "尽快", "今天", "明天"]
        for msg in conversation_history:
            if msg.role == "user":
                content = self._message_to_text(msg)

                for keyword in time_keywords:
                    if keyword in content:
                        constraints["time_sensitive"] = True
                        break

        return constraints

    def enhance_query(
        self,
        query: str,
        context: dict
    ) -> str:
        """
        使用上下文增强查询

        Args:
            query: 原始查询
            context: 对话上下文

        Returns:
            str: 增强后的查询
        """
        try:
            enhanced_parts = [query]

            # 添加实体信息
            entities = context.get("entities", [])
            if entities:
                entity_values = [e["value"] for e in entities[:3]]
                enhanced_parts.extend(entity_values)

            # 添加主题信息
            topics = context.get("topics", [])
            if topics:
                enhanced_parts.extend(topics[:2])

            # 添加偏好信息
            preferences = context.get("preferences", [])
            if preferences:
                # 提取正面偏好
                positive_prefs = [
                    p.split(":", 1)[1] for p in preferences
                    if p.startswith("positive:")
                ]
                enhanced_parts.extend(positive_prefs[:2])

            enhanced_query = " ".join(enhanced_parts)

            logger.debug(f"查询增强: {query} -> {enhanced_query[:100]}...")

            return enhanced_query

        except Exception as e:
            logger.error(f"查询增强失败: {e}")
            return query

    @staticmethod
    def _message_to_text(message: Message) -> str:
        """
        将消息转换为文本

        Args:
            message: 消息对象

        Returns:
            str: 消息文本内容
        """
        if isinstance(message.content, str):
            return message.content
        elif isinstance(message.content, list):
            # 提取文本内容
            text_parts = []
            for item in message.content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            return " ".join(text_parts)
        else:
            return ""


# 全局ConversationContext实例
conversation_context = ConversationContext()
