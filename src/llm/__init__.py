"""
Multi-LLM Integration Module

Provides comprehensive multi-LLM provider support for the multi-agent system.
Includes intelligent routing, failover, cost optimization, and unified interfaces.
"""

# Legacy single-provider support (maintained for backward compatibility)
from .client import OpenAIClient, get_llm_client
from .prompts import PromptManager, get_prompt_manager
from .response_parser import ResponseParser, parse_structured_response

# Multi-LLM provider system
from .multi_llm_client import MultiLLMClient, get_multi_llm_client, shutdown_multi_llm_client
from .provider_manager import ProviderManager
from .intelligent_router import IntelligentRouter, RoutingStrategy, RoutingContext
from .failover_system import FailoverSystem
from .cost_optimizer import CostOptimizer
from .config_manager import ConfigManager
from .enhanced_base_agent import MultiLLMBaseAgent, MultiLLMAgentMixin

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
    # Legacy support
    "OpenAIClient",
    "get_llm_client", 
    "PromptManager",
    "get_prompt_manager",
    "ResponseParser",
    "parse_structured_response",
    
    # Multi-LLM system
    "MultiLLMClient",
    "get_multi_llm_client",
    "shutdown_multi_llm_client",
    "ProviderManager",
    "IntelligentRouter",
    "FailoverSystem",
    "CostOptimizer",
    "ConfigManager",
    "MultiLLMBaseAgent",
    "MultiLLMAgentMixin",
    
    # Configuration
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
    
    # Base models
    "BaseProvider",
    "LLMRequest",
    "LLMResponse", 
    "RequestType",
    "ProviderError",
    "RateLimitError",
    "AuthenticationError",
    "ModelNotFoundError"
]