"""
Appointment Time Parser - 邀约时间解析器

负责将自然语言时间表达转换为具体的Unix时间戳。

核心功能:
- 解析相对时间表达（明天下午、下周三等）
- 解析绝对时间表达（2024年1月15日下午3点等）
- 处理模糊时间表达（周末、下个月等）
- 返回13位毫秒级Unix时间戳
"""

from datetime import datetime, timedelta
import re
from typing import Optional, Tuple, Dict, Any

from .time_utils import get_current_datetime


class AppointmentTimeParser:
    """
    邀约时间解析器

    支持中文自然语言时间表达的解析和转换。
    """

    def __init__(self):
        """初始化时间解析器"""
        self.current_time = get_current_datetime()

        # 时间关键词映射
        self.time_patterns = {
            # 相对天数
            '今天': 0,
            '明天': 1,
            '后天': 2,
            '大后天': 3,
            '昨天': -1,
            '前天': -2,

            # 周几
            '周一': 0, '星期一': 0, '周1': 0, '星期1': 0,
            '周二': 1, '星期二': 1, '周2': 1, '星期2': 1,
            '周三': 2, '星期三': 2, '周3': 2, '星期3': 2,
            '周四': 3, '星期四': 3, '周4': 3, '星期4': 3,
            '周五': 4, '星期五': 4, '周5': 4, '星期5': 4,
            '周六': 5, '星期六': 5, '周6': 5, '星期6': 5,
            '周日': 6, '星期日': 6, '周7': 6, '星期7': 6,
            '周末': 5, '这个周末': 5, '这周末': 5,

            # 相对周
            '下周': 7, '下个周': 7,
            '这周': 0, '本周': 0, '这星期': 0, '本星期': 0,
            '上周': -7, '上个周': -7, '上个星期': -7, '上星期': -7,

            # 相对月
            '下个月': 30, '下月': 30,
            '这个月': 0, '本月': 0,
            '上个月': -30, '上月': -30,
        }

        # 时段映射
        self.period_mapping = {
            '上午': (9, 12),
            '中午': (12, 14),
            '下午': (14, 18),
            '晚上': (18, 21),
            '早': (8, 10),
            '晚': (19, 21),
            '凌晨': (6, 8),
            '深夜': (22, 23),
        }

        # 具体时间点的正则表达式
        self.time_regex = re.compile(r'(\d{1,2})[点时](\d{1,2})?分?')
        self.date_regex = re.compile(r'(\d{1,2})[月/](\d{1,2})[日号]?')

    def parse_time_expression(self, time_expression: str) -> Tuple[Optional[int], Dict[str, Any]]:
        """
        解析时间表达，返回时间戳和解析信息

        Args:
            time_expression: 时间表达字符串，如"明天下午3点"

        Returns:
            Tuple[int, Dict]: (时间戳毫秒, 解析信息)
        """
        try:
            if not time_expression or not isinstance(time_expression, str):
                return None, {"error": "无效的时间表达", "original": time_expression}

            time_expression = time_expression.strip()
            self.current_time = get_current_datetime()  # 每次解析时更新当前时间

            # 解析策略 - 优先级调整，增强对常见表达的容错性
            timestamp = None
            parse_info = {
                "original": time_expression,
                "method": "unknown",
                "confidence": 0.0,
                "parsed_components": {}
            }

            # 1. 尝试解析相对时间 + 时段 (最常见的表达，如"明天下午")
            timestamp, info = self._parse_relative_with_period(time_expression)
            if timestamp and info["confidence"] > 0.5:  # 降低置信度要求
                timestamp, parse_info = timestamp, info

            # 2. 尝试解析相对时间 + 具体时间
            if not timestamp:
                timestamp, info = self._parse_relative_with_exact_time(time_expression)
                if timestamp and info["confidence"] > 0.5:  # 降低置信度要求
                    timestamp, parse_info = timestamp, info

            # 3. 尝试解析相对天数 (单独的"明天"、"后天"等)
            if not timestamp:
                timestamp, info = self._parse_relative_days(time_expression)
                if timestamp and info["confidence"] > 0.3:  # 进一步降低置信度要求
                    timestamp, parse_info = timestamp, info

            # 4. 尝试解析绝对日期时间
            if not timestamp:
                timestamp, info = self._parse_absolute_datetime(time_expression)
                if timestamp and info["confidence"] > 0.6:
                    timestamp, parse_info = timestamp, info

            # 5. 模糊时间处理
            if not timestamp:
                timestamp, info = self._parse_fuzzy_time(time_expression)
                if timestamp:
                    timestamp, parse_info = timestamp, info

            if timestamp:
                # 转换为13位毫秒时间戳
                timestamp_ms = int(timestamp.timestamp() * 1000)
                parse_info["timestamp_ms"] = timestamp_ms
                parse_info["timestamp_readable"] = timestamp.isoformat()
                return timestamp_ms, parse_info
            else:
                return None, {**parse_info, "error": "无法解析时间表达"}

        except Exception as e:
            return None, {"error": f"解析失败: {str(e)}", "original": time_expression}

    def _parse_relative_with_period(self, expression: str) -> Tuple[Optional[datetime], Dict[str, Any]]:
        """解析相对时间 + 时段，如"明天下午"、"下周三晚上"""
        parse_info = {"method": "relative_with_period", "confidence": 0.0, "parsed_components": {}}

        # 查找相对时间关键词
        for keyword, days_offset in self.time_patterns.items():
            if keyword in expression:
                base_date = self.current_time + timedelta(days=days_offset)
                parse_info["parsed_components"]["relative_day"] = keyword

                # 查找时段
                for period, (start_hour, end_hour) in self.period_mapping.items():
                    if period in expression:
                        # 取时段的中间时间
                        target_hour = (start_hour + end_hour) // 2
                        target_time = base_date.replace(hour=target_hour, minute=0, second=0, microsecond=0)

                        parse_info.update({
                            "confidence": 0.9,
                            "parsed_components": {
                                **parse_info["parsed_components"],
                                "period": period,
                                "target_hour": target_hour,
                                "base_date": base_date.date().isoformat()
                            }
                        })
                        return target_time, parse_info

        return None, parse_info

    def _parse_relative_with_exact_time(self, expression: str) -> Tuple[Optional[datetime], Dict[str, Any]]:
        """解析相对时间 + 具体时间，如"明天下午3点"、"下周三14:30"""
        parse_info = {"method": "relative_with_exact_time", "confidence": 0.0, "parsed_components": {}}

        # 查找相对时间关键词
        for keyword, days_offset in self.time_patterns.items():
            if keyword in expression:
                base_date = self.current_time + timedelta(days=days_offset)
                parse_info["parsed_components"]["relative_day"] = keyword

                # 查找具体时间
                time_match = self.time_regex.search(expression)
                if time_match:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2) or 0)

                    # 验证时间有效性
                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                        target_time = base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

                        parse_info.update({
                            "confidence": 0.95,
                            "parsed_components": {
                                **parse_info["parsed_components"],
                                "exact_time": f"{hour:02d}:{minute:02d}",
                                "hour": hour,
                                "minute": minute,
                                "base_date": base_date.date().isoformat()
                            }
                        })
                        return target_time, parse_info

        return None, parse_info

    def _parse_absolute_datetime(self, expression: str) -> Tuple[Optional[datetime], Dict[str, Any]]:
        """解析绝对日期时间，如"1月15日下午3点"、"2024年12月20日14:30"""
        parse_info = {"method": "absolute_datetime", "confidence": 0.0, "parsed_components": {}}

        # 查找日期
        date_match = self.date_regex.search(expression)
        if date_match:
            month = int(date_match.group(1))
            day = int(date_match.group(2))

            # 查找时间
            time_match = self.time_regex.search(expression)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2) or 0)
            else:
                # 查找时段
                hour = None
                for period, (start_hour, end_hour) in self.period_mapping.items():
                    if period in expression:
                        hour = (start_hour + end_hour) // 2
                        parse_info["parsed_components"]["period"] = period
                        break

                # 如果没有具体时间，使用默认时间
                if hour is None:
                    hour = 14  # 默认下午2点

            # 构建日期时间
            try:
                current_year = self.current_time.year
                target_time = self.current_time.replace(
                    year=current_year,
                    month=month,
                    day=day,
                    hour=hour,
                    minute=minute,
                    second=0,
                    microsecond=0
                )

                # 如果日期已过，则设为明年
                if target_time < self.current_time:
                    target_time = target_time.replace(year=current_year + 1)

                parse_info.update({
                    "confidence": 0.9,
                    "parsed_components": {
                        "absolute_date": f"{month}月{day}日",
                        "time": f"{hour:02d}:{minute:02d}",
                        "month": month,
                        "day": day,
                        "hour": hour,
                        "minute": minute,
                        **parse_info["parsed_components"]
                    }
                })
                return target_time, parse_info

            except ValueError as e:
                parse_info["error"] = f"无效的日期: {str(e)}"

        return None, parse_info

    def _parse_relative_days(self, expression: str) -> Tuple[Optional[datetime], Dict[str, Any]]:
        """解析相对天数，如"明天"、"后天"、"下周"""
        parse_info = {"method": "relative_days", "confidence": 0.0, "parsed_components": {}}

        for keyword, days_offset in self.time_patterns.items():
            if keyword in expression:
                target_time = self.current_time + timedelta(days=days_offset)

                parse_info.update({
                    "confidence": 0.7 if days_offset <= 3 else 0.5,
                    "parsed_components": {
                        "relative_day": keyword,
                        "days_offset": days_offset,
                        "target_date": target_time.date().isoformat()
                    }
                })
                return target_time, parse_info

        return None, parse_info

    def _parse_fuzzy_time(self, expression: str) -> Tuple[Optional[datetime], Dict[str, Any]]:
        """解析模糊时间，如"最近"、"这几天"、"有空的时候"""
        parse_info = {"method": "fuzzy_time", "confidence": 0.0, "parsed_components": {}}

        fuzzy_keywords = {
            '最近': 3,
            '这几天': 3,
            '有空': 7,
            '方便': 7,
            '随时': 1,
        }

        for keyword, days_offset in fuzzy_keywords.items():
            if keyword in expression:
                target_time = self.current_time + timedelta(days=days_offset)

                parse_info.update({
                    "confidence": 0.3,
                    "parsed_components": {
                        "fuzzy_term": keyword,
                        "estimated_days": days_offset,
                        "target_date": target_time.date().isoformat()
                    }
                })
                return target_time, parse_info

        return None, {"method": "fuzzy_time", "confidence": 0.0, "error": "未识别的时间表达"}


def parse_appointment_time(time_expression: str) -> Tuple[Optional[int], Dict[str, Any]]:
    """
    便捷函数：解析邀约时间表达

    Args:
        time_expression: 时间表达字符串

    Returns:
        Tuple[int, Dict]: (时间戳毫秒, 解析信息)
    """
    parser = AppointmentTimeParser()
    return parser.parse_time_expression(time_expression)