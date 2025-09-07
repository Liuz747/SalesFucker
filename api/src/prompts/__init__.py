"""
默认提示词模块

该模块包含系统的默认提示词模板，支持租户自定义覆盖。
提供多智能体系统的基础提示词配置。

核心功能:
- 默认提示词模板管理
- 租户自定义提示词集成
- 提示词缓存和性能优化
- 智能体个性化配置
"""

from .prompt_manager import PromptManager, get_prompt_manager
from .templates import get_default_prompts

__all__ = [
    "PromptManager",
    "get_prompt_manager", 
    "get_default_prompts"
]