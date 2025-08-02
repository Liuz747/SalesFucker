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


class ProcessingConstants:
    """
    处理常量类
    
    定义系统处理相关的常量和默认值。
    """
    
    # 超时配置（毫秒）
    DEFAULT_TIMEOUT = 5000
    COMPLIANCE_TIMEOUT = 2000
    AGENT_TIMEOUT = 3000
    WORKFLOW_TIMEOUT = 10000
    
    # 重试配置
    MAX_RETRIES = 3
    RETRY_DELAY_MS = 1000
    
    # 性能阈值
    WARNING_ERROR_RATE = 10.0
    CRITICAL_ERROR_RATE = 20.0
    MAX_PROCESSING_TIME_MS = 5000
    
    # 队列限制
    MAX_QUEUE_SIZE = 1000
    MAX_BATCH_SIZE = 50


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
    RESPONSE_NODE = "response_generator"
    
    # 市场策略
    PREMIUM_STRATEGY = "premium"
    BUDGET_STRATEGY = "budget"
    YOUTH_STRATEGY = "youth"
    MATURE_STRATEGY = "mature"


class AgentConstants:
    """
    智能体常量类
    
    定义智能体相关的常量。
    """
    
    # 智能体类型
    COMPLIANCE_AGENT = "compliance"
    SALES_AGENT = "sales"
    PRODUCT_AGENT = "product_expert"
    MEMORY_AGENT = "memory"
    SENTIMENT_AGENT = "sentiment"
    INTENT_AGENT = "intent"
    
    # 智能体状态
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class ErrorConstants:
    """
    错误常量类
    
    定义错误相关的常量。
    """
    
    # 错误类型
    VALIDATION_ERROR = "validation_error"
    PROCESSING_ERROR = "processing_error"
    TIMEOUT_ERROR = "timeout_error"
    AGENT_ERROR = "agent_error"
    WORKFLOW_ERROR = "workflow_error"
    
    # 错误级别
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ConfigConstants:
    """
    配置常量类
    
    定义系统配置相关的常量。
    """
    
    # 默认配置
    DEFAULT_TENANT = "default"
    DEFAULT_CUSTOMER = "anonymous"
    DEFAULT_LANGUAGE = "zh-CN"
    
    # 特性开关
    ENABLE_COMPLIANCE = True
    ENABLE_MEMORY = True
    ENABLE_ANALYTICS = True
    ENABLE_HUMAN_LOOP = True
    ENABLE_MULTIMODAL = True


class MultiModalConstants:
    """
    多模态处理常量类
    
    定义多模态处理相关的常量和配置。
    """
    
    # 文件大小限制（字节）
    MAX_AUDIO_SIZE = 25 * 1024 * 1024  # 25MB
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    
    # 处理时间限制（毫秒）
    VOICE_PROCESSING_TIMEOUT = 30000  # 30秒
    IMAGE_PROCESSING_TIMEOUT = 15000  # 15秒
    
    # 质量配置
    MIN_AUDIO_DURATION = 0.5  # 0.5秒
    MAX_AUDIO_DURATION = 60.0  # 60秒
    MIN_IMAGE_WIDTH = 200
    MIN_IMAGE_HEIGHT = 200
    
    # 批处理配置
    MAX_BATCH_IMAGES = 5
    MAX_CONCURRENT_PROCESSING = 10
    
    # 缓存配置
    VOICE_CACHE_TTL = 3600  # 1小时
    IMAGE_CACHE_TTL = 86400  # 24小时
    
    # 置信度阈值
    MIN_VOICE_CONFIDENCE = 0.7
    MIN_IMAGE_CONFIDENCE = 0.6
    MIN_SKIN_ANALYSIS_CONFIDENCE = 0.5
    
    # 支持的语言
    SUPPORTED_LANGUAGES = ["zh", "en"]
    DEFAULT_VOICE_LANGUAGE = "zh" 