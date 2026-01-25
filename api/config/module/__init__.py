from .intent_config import IntentThresholdConfig
from .rag_config import RAGConfig


class ModuleConfig(
    IntentThresholdConfig,
    RAGConfig,
):
    pass