"""
提示词模板加载器
"""

from pathlib import Path
from typing import Optional

from jinja2 import Template

from utils import load_yaml_file, get_component_logger

logger = get_component_logger(__name__)


def get_prompt_template(template_name: str, **context) -> Optional[str]:
    """
    根据模板名称获取提示词模板

    Args:
        template_name: 模板名称 (ice_breaking, role_prompt, thread_context_prompt, etc.)
        **context: 传递给Jinja2的上下文变量

    Returns:
        Optional[str]: 模板字符串，如果不存在则返回None

    Examples:
        # 获取模板字符串
        >>> rendered = get_prompt_template("role_prompt",
        ...                                 name_display="小美",
        ...                                 occupation="美妆顾问")
    """
    try:
        # 获取模板文件路径
        current_dir = Path(__file__).parent
        template_path = current_dir / "templates" / "system_prompt.yaml"

        # 加载YAML配置
        config = load_yaml_file(template_path)

        # 获取指定模板配置
        template_config = config.get(template_name)

        if not template_config:
            return None

        template = Template(
            template_config.get("template"),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False
        )
        return template.render(**context)

    except Exception as e:
        logger.error(f"模板渲染失败: {template_name}, 错误: {e}", exc_info=True)
        raise