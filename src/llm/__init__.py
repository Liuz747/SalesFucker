"""
LLM Integration Module

Provides OpenAI and LangChain integration for the multi-agent system.
Centralizes all LLM-related functionality for consistent usage across agents.
"""

from .client import OpenAIClient, get_llm_client
from .prompts import PromptManager, get_prompt_manager
from .response_parser import ResponseParser, parse_structured_response

__all__ = [
    "OpenAIClient",
    "get_llm_client", 
    "PromptManager",
    "get_prompt_manager",
    "ResponseParser",
    "parse_structured_response"
]