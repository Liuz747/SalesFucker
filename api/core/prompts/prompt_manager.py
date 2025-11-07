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

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Template, TemplateNotFound
from utils import get_component_logger

logger = get_component_logger(__name__)

# 全局模板缓存
_template_cache: Dict[str, Dict[str, str]] = {}
_yaml_cache: Dict[str, Any] = {}

def _load_agent_templates() -> Dict[str, Any]:
    """加载agent模板配置文件"""
    global _yaml_cache

    if "agent_templates" in _yaml_cache:
        return _yaml_cache["agent_templates"]

    try:
        template_path = Path(__file__).parent / "templates" / "agent.yaml"
        if not template_path.exists():
            logger.error(f"Agent template file not found: {template_path}")
            return {}

        with open(template_path, 'r', encoding='utf-8') as f:
            templates = yaml.safe_load(f) or {}

        _yaml_cache["agent_templates"] = templates
        logger.info(f"Loaded agent templates from {template_path}")
        return templates

    except Exception as e:
        logger.error(f"Failed to load agent templates: {e}")
        return {}

def render_agent_prompt(agent_name: str, template_name: str, **kwargs) -> str:
    """
    渲染agent提示词模板

    Args:
        agent_name: agent名称 (如 'sales', 'sentiment')
        template_name: 模板名称 (如 'chat_with_sentiment', 'sentiment_analysis')
        **kwargs: 模板变量

    Returns:
        渲染后的提示词字符串
    """
    try:
        # 加载模板配置
        templates = _load_agent_templates()

        # 获取指定agent的模板
        agent_templates = templates.get("agents", {}).get(agent_name, {})
        if not agent_templates:
            logger.error(f"No templates found for agent: {agent_name}")
            return f"Error: No templates found for agent '{agent_name}'"

        # 获取指定模板
        template_config = agent_templates.get(template_name)
        if not template_config:
            logger.error(f"Template '{template_name}' not found for agent '{agent_name}'")
            available_templates = list(agent_templates.keys())
            logger.info(f"Available templates for {agent_name}: {available_templates}")
            return f"Error: Template '{template_name}' not found for agent '{agent_name}'. Available: {available_templates}"

        template_str = template_config.get("template", "")
        if not template_str:
            logger.error(f"Template '{template_name}' for agent '{agent_name}' has no content")
            return f"Error: Template '{template_name}' has no content"

        # 使用Jinja2渲染模板
        jinja_template = Template(template_str)
        rendered_prompt = jinja_template.render(**kwargs)

        logger.debug(f"Rendered template '{agent_name}.{template_name}' with {len(kwargs)} variables")
        return rendered_prompt.strip()

    except TemplateNotFound as e:
        logger.error(f"Template rendering failed - template not found: {e}")
        return f"Error: Template not found - {e}"
    except Exception as e:
        logger.error(f"Failed to render prompt template {agent_name}.{template_name}: {e}")
        return f"Error: Failed to render template - {e}"

def get_available_templates(agent_name: Optional[str] = None) -> Dict[str, Any]:
    """
    获取可用的模板列表

    Args:
        agent_name: 可选，指定agent名称。如果为None，返回所有agent的模板

    Returns:
        模板信息字典
    """
    templates = _load_agent_templates()

    if agent_name:
        return templates.get("agents", {}).get(agent_name, {})
    else:
        return templates.get("agents", {})
