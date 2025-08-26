"""
YAML工具函数

提供通用的YAML文件加载功能
"""

import yaml
from typing import Dict, Any
from pathlib import Path


def load_yaml_file(file_path: str) -> Dict[str, Any]:
    """
    加载YAML文件
    
    参数:
        file_path: YAML文件路径
        
    返回:
        Dict[str, Any]: 解析后的YAML内容
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"YAML文件不存在: {file_path}")
    
    with open(path, encoding="utf-8") as f:
        try:
            return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"YAML文件解析失败: {e}")