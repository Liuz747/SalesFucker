"""
Sentiment Analysis Agent Module

Provides AI-powered emotion detection and sentiment analysis for customer interactions.
Integrates with the multi-agent system to provide emotional context for conversations.
"""

from .agent import SentimentAnalysisAgent
from .response_adaptation import SalesResponseAdapter

__all__ = ["SentimentAnalysisAgent", "SalesResponseAdapter"]
