"""
主动触发的提示词模板加载器
"""

from pathlib import Path
from typing import Optional

from utils.yaml_loader import load_yaml_file


def get_prompt_template(task_name: str) -> Optional[str]:
    """
    根据任务名称获取提示词模板

    Args:
        task_name: 任务名称 (ice_breaking, follow_up, holiday, etc.)

    Returns:
        Optional[str]: 模板字符串，如果不存在则返回None
    """
    try:
        # 获取模板文件路径
        current_dir = Path(__file__).parent
        template_path = current_dir / "templates" / "active_trigger.yaml"

        # 加载YAML配置
        config = load_yaml_file(template_path)

        # 获取指定任务的模板
        task_config = config.get(task_name)

        if task_config:
            return task_config.get("template")

        return None

    except Exception:
        return None