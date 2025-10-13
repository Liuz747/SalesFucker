"""
Elasticsearch Memory Integration

This package handles all customer memory and context management:
- Multi-tenant customer profiles
- Complete conversation history storage (user messages + LLM responses)
- Behavioral pattern tracking
- Context retrieval and persistence
- High-performance multi-level caching

Architecture:
- HighPerformanceStore: Customer profiles with multi-level caching
- ConversationStore: Complete message history with intelligent indexing
- ConnectionPoolManager: Multi-tenant connection management
"""

from .conversation_store import ConversationStore

__all__ = [
    'ConversationStore'
] 