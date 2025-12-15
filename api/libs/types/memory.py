from enum import StrEnum


class MemoryType(StrEnum):
    """
    记忆类型枚举
    
    定义系统支持的所有记忆类型，用于Elasticsearch索引和查询分类。
    """
    LONG_TERM = "long_term"                         # 长期记忆（对话摘要）
    EPISODIC = "episodic"                           # 情景记忆（特定事件）
    FEEDBACK = "feedback"                           # 线下报告
    MOMENTS_INTERACTION = "moments_interaction"     # 朋友圈互动记录

