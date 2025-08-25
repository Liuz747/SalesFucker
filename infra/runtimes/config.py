"""
LLM配置加载器

从环境变量和配置文件加载LLM供应商配置。
支持OpenAI、Anthropic等多个供应商的配置管理。
"""

from typing import Optional, Dict, Any

from infra.runtimes.entities import Provider
from config import settings

class LLMConfig:
    """LLM配置管理器"""

    def __init__(self):
        """初始化配置加载器"""
        self.openai = self._load_openai_config()
        self.anthropic = self._load_anthropic_config()
        # self.gemini = self._load_gemini_config()
        # self.deepseek = self._load_deepseek_config()
        self.routing_config = self._load_routing_config()

    def _load_openai_config(self) -> Optional[Provider]:
        """
        加载OpenAI配置
        
        返回:
            Optional[Provider]: OpenAI配置，如果API密钥不存在则返回None
        """
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            return None

        return Provider(
            api_key=api_key,
            models=["gpt-4o", "gpt-4o-mini"],
            enabled=True
        )

    def _load_anthropic_config(self) -> Optional[Provider]:
        """
        加载Anthropic配置
        
        返回:
            Optional[Provider]: Anthropic配置，如果API密钥不存在则返回None
        """
        api_key = settings.ANTHROPIC_API_KEY
        if not api_key:
            return None

        return Provider(
            api_key=api_key,
            models=["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
            enabled=True
        )

    # 其他供应商配置方法类似...

    def _load_routing_config(self) -> Dict[str, Any]:
        """
        加载路由配置
        
        返回:
            Dict[str, Any]: 路由配置字典
        """
        return {
            "default_provider": settings.DEFAULT_LLM_PROVIDER,
            "fallback_provider": settings.FALLBACK_LLM_PROVIDER,
            "enable_chinese_routing": True,
            "enable_vision_routing": True
        }
