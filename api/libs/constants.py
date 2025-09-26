"""
系统常量模块

集中管理所有系统常量，消除散布在各文件中的重复常量定义。

核心功能:
- 状态常量
- 处理常量
- 消息常量
- 超时配置
"""


class StatusConstants:
    """
    状态常量类
    
    统一系统中所有状态相关的常量定义。
    """
    
    # 健康状态
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    
    # 处理状态
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    
    # 合规状态
    APPROVED = "approved"
    FLAGGED = "flagged"
    BLOCKED = "blocked"


class MessageConstants:
    """
    消息常量类
    
    定义消息系统相关的常量。
    """
    
    # 消息类型
    QUERY = "query"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    TRIGGER = "trigger"
    SUGGESTION = "suggestion"
    
    # 消息优先级
    LOW_PRIORITY = "low"
    MEDIUM_PRIORITY = "medium"
    HIGH_PRIORITY = "high"
    URGENT_PRIORITY = "urgent"
    
    # 输入类型
    TEXT_INPUT = "text"
    VOICE_INPUT = "voice"
    IMAGE_INPUT = "image"
    MULTIMODAL_INPUT = "multimodal"
    
    # 多模态处理类型
    VOICE_TRANSCRIPTION = "voice_transcription"
    IMAGE_ANALYSIS = "image_analysis"
    SKIN_ANALYSIS = "skin_analysis"
    PRODUCT_RECOGNITION = "product_recognition"
    
    # 多模态文件格式
    SUPPORTED_AUDIO_FORMATS = ["mp3", "wav", "m4a", "ogg", "webm"]
    SUPPORTED_IMAGE_FORMATS = ["jpg", "jpeg", "png", "webp"]
    
    # 多模态处理状态
    UPLOADING = "uploading"
    PROCESSING = "processing"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    ERROR = "error"


class WorkflowConstants:
    """
    工作流常量类
    
    定义工作流相关的常量。
    """
    
    # 节点名称
    COMPLIANCE_NODE = "compliance_review"
    SENTIMENT_NODE = "sentiment_analysis"
    INTENT_NODE = "intent_analysis"
    STRATEGY_NODE = "market_strategy"
    SALES_NODE = "sales_agent"
    PRODUCT_NODE = "product_expert"
    MEMORY_NODE = "memory_agent"