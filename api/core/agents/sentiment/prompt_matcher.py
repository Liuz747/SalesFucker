"""
极简提示词匹配器 - 纯数据驱动，零逻辑
"""

import json
from pathlib import Path
from typing import Any, Optional


class PromptMatcher:
    """
    纯查表引擎 - 输入坐标，输出提示词

    功能：
    1. 根据情感分数映射到维度（low/medium/high）
    2. 结合旅程阶段构建查找键
    3. 从配置文件中查表返回对应提示词
    4. 支持配置热重载
    """

    def __init__(self, config_path: Optional[str] = None):
        """初始化并加载配置文件"""
        if config_path is None:
            config_path = Path(__file__).parent / "prompt_config.json"

        self.config_path = config_path
        self._load_config()

    def _load_config(self) -> None:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"提示词配置文件未找到: {self.config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"提示词配置文件格式错误: {e}")

    def _map_sentiment_level(self, score: float) -> str:
        """
        情感分数 → 维度映射

        Args:
            score: 0.0-1.0 的情感分数

        Returns:
            "low" | "medium" | "high"
        """
        for level, config in self.config["dimensions"]["sentiment"].items():
            min_score, max_score = config["range"]
            if min_score <= score < max_score:
                return level

        # 处理边界情况（score = 1.0）
        if score == 1.0:
            return "high"

        # 默认返回 medium
        return "medium"

    def get_prompt(
        self,
        sentiment_score: float,
        journey_stage: str
    ) -> dict[str, Any]:
        """
        核心方法：纯查表

        Args:
            sentiment_score: 0.0-1.0 的情感分数
            journey_stage: "awareness" | "consideration" | "decision"

        Returns:
            匹配的提示词配置，包含：
            - system_prompt: 系统提示词内容
            - tone: 语气描述
            - strategy: 策略描述
            - matched_key: 匹配的键（调试用）
            - sentiment_level: 映射后的情感维度
            - journey_stage: 旅程阶段
            - sentiment_score: 原始情感分数
        """
        # 1. 映射情感维度
        sentiment_level = self._map_sentiment_level(sentiment_score)

        # 2. 构建查找键
        key = f"{sentiment_level}_{journey_stage}"

        # 3. 查表获取提示词配置
        prompt_config = self.config["prompt_matrix"].get(
            key,
            self.config["fallback_prompt"]  # 兜底配置
        )

        # 4. 返回增强的结果
        return {
            **prompt_config,
            "matched_key": key,
            "sentiment_level": sentiment_level,
            "journey_stage": journey_stage,
            "sentiment_score": sentiment_score
        }
