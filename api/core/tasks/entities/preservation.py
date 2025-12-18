"""Conversation Preservation Entities"""
from typing import Any, Optional

from pydantic import BaseModel


class PreservationResult(BaseModel):
    """对话保存结果"""
    success: bool
    action: str  # preserved, skipped, filtered, preservation_failed, workflow_error
    reason: str
    metadata: Optional[dict[str, Any]] = None
