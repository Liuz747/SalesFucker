"""
Do Not Disturb (DND) Helper

免打扰时间检查工具，用于判断当前时间是否在免打扰时段内
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from config import mas_config
from utils import get_component_logger

logger = get_component_logger(__name__)


def is_dnd_active(timezone: str | None = None) -> bool:
    """
    检查当前时间是否在免打扰时段内

    支持跨天的免打扰时段（例如 22:00 - 08:00）

    Args:
        timezone: 时区字符串（例如 "Asia/Shanghai"），None 则使用配置默认值

    Returns:
        bool: True 表示当前在免打扰时段内，不应发送消息

    Examples:
        >>> # DND: 22:00 - 08:00, 当前时间: 23:00
        >>> is_dnd_active()  # True

        >>> # DND: 22:00 - 08:00, 当前时间: 10:00
        >>> is_dnd_active()  # False

        >>> # DND: 22:00 - 08:00, 当前时间: 07:00
        >>> is_dnd_active()  # True
    """
    # 如果 DND 功能未启用，直接返回 False
    if not mas_config.DND_ENABLED:
        return False

    # 使用配置的时区或默认时区
    tz_str = timezone or mas_config.APP_TIMEZONE
    tz = ZoneInfo(tz_str)

    # 获取当前时间（指定时区）
    now = datetime.now(tz)
    current_hour = now.hour

    start_hour = mas_config.DND_START_HOUR
    end_hour = mas_config.DND_END_HOUR

    # 处理跨天情况（例如 00:00 - 08:00）
    if start_hour > end_hour:
        # 跨天：如果当前小时 >= 起始小时 或 < 结束小时，则在 DND 时段内
        return current_hour >= start_hour or current_hour < end_hour
    else:
        # 不跨天：如果当前小时在 [start_hour, end_hour) 内，则在 DND 时段内
        return start_hour <= current_hour < end_hour
