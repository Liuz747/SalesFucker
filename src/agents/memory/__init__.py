"""
Memory Agent Module

Provides customer profile management and conversation context persistence.
Integrates with Elasticsearch for scalable memory storage.
"""

from .agent import MemoryAgent

__all__ = ["MemoryAgent"]