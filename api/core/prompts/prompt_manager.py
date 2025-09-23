"""
提示词管理器

该模块提供统一的提示词管理服务，整合默认提示词模板和租户自定义配置。
支持缓存、热更新和降级处理。

核心功能:
- 默认提示词加载
- 租户自定义提示词获取
- 提示词缓存和性能优化
- 降级和容错处理
"""

from typing import Dict, Any, Optional
import asyncio
from datetime import datetime, timedelta

from .templates import (
    get_default_prompt, get_agent_default_prompts, 
    AgentType, PromptType, DEFAULT_PROMPTS
)
from utils import get_component_logger


class PromptManager:
    """
    提示词管理器
    
    负责管理默认提示词和租户自定义提示词，提供统一的提示词获取接口。
    """
    
    def __init__(self, enable_api_integration: bool = True):
        """
        初始化提示词管理器
        
        参数:
            enable_api_integration: 是否启用API集成（默认启用）
        """
        self.logger = get_component_logger(__name__, "PromptManager")
        self.enable_api_integration = enable_api_integration
        
        # 提示词缓存
        self._prompt_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=30)  # 缓存30分钟
        
        # 提示词处理器（用于获取租户自定义提示词）
        self._prompt_handler = None
        if self.enable_api_integration:
            try:
                from legacy_api.services.prompts_handler import PromptHandler
                self._prompt_handler = PromptHandler()
                self.logger.info("提示词处理器集成已启用")
            except Exception as e:
                self.logger.warning(f"提示词处理器集成失败，使用默认提示词: {e}")
                self.enable_api_integration = False
        
        self.logger.info("提示词管理器初始化完成")
    
    async def get_system_prompt(
        self,
        agent_id: str,
        agent_type: str,
        tenant_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        获取智能体系统提示词
        
        优先级：租户自定义 > 默认模板
        
        参数:
            agent_id: 智能体ID  
            agent_type: 智能体类型
            tenant_id: 租户ID
            context: 上下文变量
            
        返回:
            系统提示词字符串
        """
        try:
            self.logger.debug(f"获取系统提示词: agent_id={agent_id}, agent_type={agent_type}")
            
            # 尝试获取租户自定义提示词
            if self.enable_api_integration and self._prompt_handler:
                custom_prompt = await self._get_custom_system_prompt(
                    agent_id, agent_type, tenant_id, context
                )
                if custom_prompt:
                    self.logger.debug(f"使用租户自定义提示词: {agent_id}")
                    return custom_prompt
            
            # 使用默认提示词
            default_prompt = self._get_default_system_prompt(agent_type, context)
            self.logger.debug(f"使用默认系统提示词: {agent_type}")
            return default_prompt
            
        except Exception as e:
            self.logger.error(f"获取系统提示词失败: {e}")
            # 返回基础默认提示词
            return self._get_fallback_prompt(agent_type)
    
    async def get_greeting_prompt(
        self,
        agent_id: str,
        agent_type: str, 
        tenant_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        获取问候提示词
        
        参数:
            agent_id: 智能体ID
            agent_type: 智能体类型
            tenant_id: 租户ID
            context: 上下文变量
            
        返回:
            问候提示词，如果没有配置返回None
        """
        try:
            # 尝试获取租户自定义问候词
            if self.enable_api_integration and self._prompt_handler:
                custom_greeting = await self._get_custom_prompt(
                    agent_id, tenant_id, "greeting_prompt", context
                )
                if custom_greeting:
                    return custom_greeting
            
            # 使用默认问候词
            return self._get_default_prompt_by_type(agent_type, PromptType.GREETING, context)
            
        except Exception as e:
            self.logger.error(f"获取问候提示词失败: {e}")
            return None
    
    async def get_product_recommendation_prompt(
        self,
        agent_id: str,
        agent_type: str,
        tenant_id: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        获取产品推荐提示词
        
        参数:
            agent_id: 智能体ID
            agent_type: 智能体类型
            tenant_id: 租户ID
            context: 上下文变量
            
        返回:
            产品推荐提示词，如果没有配置返回None
        """
        try:
            # 尝试获取租户自定义推荐词
            if self.enable_api_integration and self._prompt_handler:
                custom_prompt = await self._get_custom_prompt(
                    agent_id, tenant_id, "product_recommendation_prompt", context
                )
                if custom_prompt:
                    return custom_prompt
            
            # 使用默认推荐词
            return self._get_default_prompt_by_type(
                agent_type, PromptType.PRODUCT_RECOMMENDATION, context
            )
            
        except Exception as e:
            self.logger.error(f"获取产品推荐提示词失败: {e}")
            return None
    
    async def _get_custom_system_prompt(
        self,
        agent_id: str,
        agent_type: str,
        tenant_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """获取租户自定义系统提示词"""
        try:
            # 检查缓存
            cache_key = f"{tenant_id}:{agent_id}:system"
            cached_prompt = self._get_from_cache(cache_key)
            if cached_prompt is not None:
                return self._apply_context_variables(cached_prompt, context)
            
            # 从提示词处理器获取
            if self._prompt_handler:
                # 使用助理ID查询自定义提示词配置
                try:
                    config_response = await self._prompt_handler.get_assistant_prompts(
                        agent_id, tenant_id
                    )
                    
                    if config_response and hasattr(config_response, 'system_prompt'):
                        custom_prompt = config_response.system_prompt
                        if custom_prompt and custom_prompt.strip():
                            # 检查是否是API返回的默认提示词（避免缓存默认值）
                            if not custom_prompt.startswith("你是一个专业的"):
                                self._set_cache(cache_key, custom_prompt)
                                return self._apply_context_variables(custom_prompt, context)
                except Exception as e:
                    self.logger.debug(f"获取助理提示词配置失败: {e}")
                    # 继续使用默认提示词
            
            return None
            
        except Exception as e:
            self.logger.warning(f"获取租户自定义系统提示词失败: {e}")
            return None
    
    async def _get_custom_prompt(
        self,
        agent_id: str,
        tenant_id: str,
        prompt_field: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """获取租户自定义特定类型提示词"""
        try:
            # 检查缓存
            cache_key = f"{tenant_id}:{agent_id}:{prompt_field}"
            cached_prompt = self._get_from_cache(cache_key)
            if cached_prompt is not None:
                return self._apply_context_variables(cached_prompt, context)
            
            # 从提示词处理器获取智能体配置
            if self._prompt_handler:
                try:
                    config_response = await self._prompt_handler.get_assistant_prompts(
                        agent_id, tenant_id
                    )
                    
                    if config_response and hasattr(config_response, prompt_field):
                        custom_prompt = getattr(config_response, prompt_field)
                        if custom_prompt and custom_prompt.strip():
                            self._set_cache(cache_key, custom_prompt)
                            return self._apply_context_variables(custom_prompt, context)
                except Exception as e:
                    self.logger.debug(f"获取助理配置失败: {e}")
                    # 继续使用默认提示词
            
            return None
            
        except Exception as e:
            self.logger.warning(f"获取租户自定义提示词失败 {prompt_field}: {e}")
            return None
    
    def _get_default_system_prompt(
        self,
        agent_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """获取默认系统提示词"""
        try:
            # 转换字符串类型到枚举
            agent_type_enum = AgentType(agent_type.lower())
            prompt = get_default_prompt(agent_type_enum, PromptType.PERSONALITY)
            
            return self._apply_context_variables(prompt, context)
            
        except ValueError:
            # 如果agent_type不在枚举中，返回通用提示词
            self.logger.warning(f"未知智能体类型: {agent_type}")
            return self._get_fallback_prompt(agent_type)
    
    def _get_default_prompt_by_type(
        self,
        agent_type: str,
        prompt_type: PromptType,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """根据类型获取默认提示词"""
        try:
            agent_type_enum = AgentType(agent_type.lower())
            prompt = get_default_prompt(agent_type_enum, prompt_type)
            
            if prompt:
                return self._apply_context_variables(prompt, context)
            
            return None
            
        except ValueError:
            self.logger.warning(f"未知智能体类型或提示词类型: {agent_type}, {prompt_type}")
            return None
    
    def _get_fallback_prompt(self, agent_type: str) -> str:
        """获取兜底提示词"""
        return f"你是一个专业的{agent_type}智能体，负责处理美妆相关的客户咨询。请提供友好、专业的服务。"
    
    def _apply_context_variables(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """应用上下文变量到提示词中"""
        if not context or not prompt:
            return prompt
        
        try:
            # 简单的变量替换实现
            for key, value in context.items():
                placeholder = f"{{{key}}}"
                if placeholder in prompt:
                    prompt = prompt.replace(placeholder, str(value))
            
            return prompt
            
        except Exception as e:
            self.logger.warning(f"应用上下文变量失败: {e}")
            return prompt
    
    def _get_cache_key(self, tenant_id: str, agent_id: str, prompt_type: str) -> str:
        """生成缓存键"""
        return f"{tenant_id}:{agent_id}:{prompt_type}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[str]:
        """从缓存获取提示词"""
        if cache_key not in self._prompt_cache:
            return None
        
        # 检查缓存是否过期
        if cache_key in self._cache_timestamps:
            cache_time = self._cache_timestamps[cache_key]
            if datetime.now() - cache_time > self._cache_ttl:
                # 缓存过期，清理
                del self._prompt_cache[cache_key]
                del self._cache_timestamps[cache_key]
                return None
        
        return self._prompt_cache[cache_key].get("content")
    
    def _set_cache(self, cache_key: str, content: str):
        """设置缓存"""
        self._prompt_cache[cache_key] = {
            "content": content,
            "created_at": datetime.now()
        }
        self._cache_timestamps[cache_key] = datetime.now()
    
    def clear_cache(self, tenant_id: Optional[str] = None):
        """清理缓存"""
        if tenant_id:
            # 清理特定租户的缓存
            keys_to_remove = [
                key for key in self._prompt_cache.keys() 
                if key.startswith(f"{tenant_id}:")
            ]
            for key in keys_to_remove:
                del self._prompt_cache[key]
                if key in self._cache_timestamps:
                    del self._cache_timestamps[key]
            
            self.logger.info(f"已清理租户 {tenant_id} 的提示词缓存")
        else:
            # 清理所有缓存
            self._prompt_cache.clear()
            self._cache_timestamps.clear()
            self.logger.info("已清理所有提示词缓存")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "total_cached_prompts": len(self._prompt_cache),
            "cache_hit_rate": "暂未实现",  # 可以添加命中率统计
            "oldest_cache": min(self._cache_timestamps.values()) if self._cache_timestamps else None,
            "newest_cache": max(self._cache_timestamps.values()) if self._cache_timestamps else None,
            "api_integration_enabled": self.enable_api_integration
        }
    
    async def get_custom_prompt(
        self,
        prompt_type: str,
        agent_id: str,
        agent_type: str,
        tenant_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        获取自定义类型提示词（用于销售智能体的异议处理等特殊需求）
        
        参数:
            prompt_type: 提示词类型（如 'objection_handling'）
            agent_id: 智能体ID
            agent_type: 智能体类型 
            tenant_id: 租户ID
            context: 上下文变量
            
        返回:
            自定义提示词，如果没有配置返回None
        """
        try:
            # 尝试获取租户自定义提示词
            if self.enable_api_integration and self._prompt_handler:
                custom_prompt = await self._get_custom_prompt(
                    agent_id, tenant_id, prompt_type, context
                )
                if custom_prompt:
                    return custom_prompt
            
            # 如果没有自定义提示词，返回None让调用方处理
            return None
            
        except Exception as e:
            self.logger.error(f"获取自定义提示词失败 {prompt_type}: {e}")
            return None

    async def preload_prompts_for_agent(self, agent_id: str, agent_type: str, tenant_id: str):
        """为智能体预加载提示词（可选的性能优化）"""
        try:
            self.logger.debug(f"预加载智能体提示词: {agent_id}")
            
            # 预加载系统提示词
            await self.get_system_prompt(agent_id, agent_type, tenant_id)
            
            # 预加载其他类型提示词
            await self.get_greeting_prompt(agent_id, agent_type, tenant_id)
            await self.get_product_recommendation_prompt(agent_id, agent_type, tenant_id)
            
            self.logger.debug(f"智能体提示词预加载完成: {agent_id}")
            
        except Exception as e:
            self.logger.warning(f"预加载智能体提示词失败: {e}")
    
    async def close(self):
        """关闭提示词管理器"""
        if self._prompt_handler:
            # 提示词处理器不需要特殊关闭操作
            self.logger.info("提示词管理器已关闭")
        self.clear_cache()


# 全局提示词管理器实例
_global_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager(enable_api_integration: bool = True) -> PromptManager:
    """获取全局提示词管理器实例"""
    global _global_prompt_manager
    
    if _global_prompt_manager is None:
        _global_prompt_manager = PromptManager(enable_api_integration)
    
    return _global_prompt_manager


async def close_prompt_manager():
    """关闭全局提示词管理器"""
    global _global_prompt_manager
    
    if _global_prompt_manager:
        await _global_prompt_manager.close()
        _global_prompt_manager = None