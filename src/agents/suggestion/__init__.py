"""
AI Suggestion Agent Module

Provides human-AI collaboration and intelligent assistance recommendations.
Handles escalation decisions and system improvement suggestions.

Components:
- AISuggestionAgent: Main orchestrator for suggestion generation
- EscalationAnalyzer: Rule-based escalation decision engine
- QualityAssessor: Conversation quality evaluation
- LLMAnalyzer: LLM-powered intelligent analysis
- SuggestionGenerator: Template-based suggestion generation
- SuggestionTemplateManager: Template management and matching
- PerformanceSuggestionGenerator: Performance-focused suggestions
- OptimizationAnalyzer: System optimization opportunity identification
"""

from .agent import AISuggestionAgent
from .escalation_analyzer import EscalationAnalyzer
from .quality_assessor import QualityAssessor
from .llm_analyzer import LLMAnalyzer
from .suggestion_generator import SuggestionGenerator
from .suggestion_templates import SuggestionTemplateManager
from .performance_suggestions import PerformanceSuggestionGenerator
from .optimization_analyzer import OptimizationAnalyzer

__all__ = [
    "AISuggestionAgent",
    "EscalationAnalyzer", 
    "QualityAssessor",
    "LLMAnalyzer",
    "SuggestionGenerator",
    "SuggestionTemplateManager",
    "PerformanceSuggestionGenerator",
    "OptimizationAnalyzer"
]