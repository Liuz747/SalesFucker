"""
Multi-LLM Integration Module

Provides comprehensive multi-LLM provider support for the multi-agent system.
Includes intelligent routing, simple retry, cost optimization, and unified interfaces.
"""

# Multi-LLM provider system
from .multi_llm_client import MultiLLMClient, get_multi_llm_client, shutdown_multi_llm_client
from .provider_manager import ProviderManager
from .intelligent_router import IntelligentRouter, RoutingStrategy, RoutingContext
from .cost_optimizer import CostOptimizer
from .config_manager import ConfigManager
from .llm_mixin import LLMMixin

# Configuration and data models
from .provider_config import (
    ProviderType,
    ProviderConfig, 
    ProviderCredentials,
    ModelConfig,
    GlobalProviderConfig,
    TenantProviderConfig,
    AgentProviderMapping,
    RoutingRule,
    CostConfig
)

# Base provider and request/response models
from .base_provider import (
    BaseProvider,
    LLMRequest,
    LLMResponse,
    RequestType,
    ProviderError,
    RateLimitError,
    AuthenticationError,
    ModelNotFoundError
)

__all__ = [
    # Multi-LLM system - core functionality
    "MultiLLMClient",
    "get_multi_llm_client", 
    "shutdown_multi_llm_client",
    "ProviderManager",
    "IntelligentRouter",
    "CostOptimizer",
    "ConfigManager",
    "LLMMixin",
    
    # Configuration models
    "ProviderType",
    "ProviderConfig",
    "ProviderCredentials", 
    "ModelConfig",
    "GlobalProviderConfig",
    "TenantProviderConfig",
    "AgentProviderMapping",
    "RoutingRule",
    "CostConfig",
    "RoutingStrategy",
    "RoutingContext",
    
    # Base provider models
    "BaseProvider",
    "LLMRequest",
    "LLMResponse", 
    "RequestType",
    "ProviderError",
    "RateLimitError",
    "AuthenticationError",
    "ModelNotFoundError"
]