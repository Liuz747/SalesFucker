from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from .responses import BaseResponse


class MemoryInsertRequest(BaseModel):
    """手动记忆插入请求"""

    thread_id: UUID = Field(description="对话线程ID")
    memories: list[str] = Field(description="原始对话文本或记忆内容", min_length=1, max_length=100)
    tags: Optional[list[str]] = Field(None, description="标签列表")

    @field_validator("memories")
    @classmethod
    def validate_memories(cls, v: list[str]) -> list[str]:
        """验证记忆列表内容"""
        # 验证每条记忆不能为空或仅包含空白字符
        for idx, memory in enumerate(v):
            if not memory or not memory.strip():
                raise ValueError(f"第{idx + 1}条记忆不能为空或仅包含空白字符")
        return v


class MemoryInsertResult(BaseModel):
    """单条记忆插入结果"""
    index: int = Field(description="记忆在请求列表中的索引")
    success: bool = Field(description="是否插入成功")
    memory_id: Optional[str] = Field(None, description="成功时返回的记忆ID")
    error: Optional[str] = Field(None, description="失败时的错误信息")


class MemoryInsertSummary(BaseModel):
    """批量插入统计摘要"""
    total: int = Field(description="总记忆数")
    succeed: int = Field(description="成功插入数")
    failed: int = Field(description="失败数")


class MemoryInsertResponse(BaseResponse):
    """手动记忆插入响应"""

    results: list[MemoryInsertResult] = Field(description="详细结果列表")


class MemoryDeleteRequest(BaseModel):
    """记忆删除请求"""

    thread_id: UUID = Field(description="对话线程ID")
    memory_id: str = Field(description="记忆ID")
