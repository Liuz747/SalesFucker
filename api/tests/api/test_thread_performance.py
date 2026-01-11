"""
线程存储性能测试

测试Redis+PostgreSQL二级存储架构的性能特征。
MessagePack序列化 + 异步数据库写入优化。
"""

import pytest
import time
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from models import Thread
from services.thread_service import ThreadService
from repositories.thread_repo import ThreadRepository


class TestThreadPerformance:
    """线程存储性能测试类"""

    @pytest.fixture
    def sample_thread(self):
        """示例线程fixture"""
        return Thread(
            thread_id=uuid4(),
            tenant_id="tenant-789",
            assistant_id=uuid4(),
            name="测试客户"
        )

    @pytest.mark.asyncio
    async def test_thread_service_get_thread(self, sample_thread):
        """测试ThreadService获取线程"""
        # Mock Redis和数据库
        with patch('services.thread_service.infra_registry') as mock_registry:
            mock_redis = AsyncMock()
            mock_registry.get_cached_clients().redis = mock_redis

            # Mock缓存未命中
            with patch.object(ThreadRepository, 'get_thread_cache', return_value=None):
                with patch.object(ThreadRepository, 'get_thread', return_value=None):
                    result = await ThreadService.get_thread(sample_thread.thread_id)
                    assert result is None

    @pytest.mark.asyncio
    async def test_messagepack_serialization_performance(self, sample_thread):
        """测试MessagePack序列化性能"""
        import json
        import msgpack
        from datetime import datetime

        # Convert thread to dict and handle UUID/datetime serialization
        thread_dict = sample_thread.model_dump()
        # Convert UUIDs to strings for serialization
        if thread_dict.get('thread_id'):
            thread_dict['thread_id'] = str(thread_dict['thread_id'])
        if thread_dict.get('assistant_id'):
            thread_dict['assistant_id'] = str(thread_dict['assistant_id'])
        # Convert datetime objects to ISO format strings
        for key, value in thread_dict.items():
            if isinstance(value, datetime):
                thread_dict[key] = value.isoformat()

        # MessagePack序列化性能
        start_time = time.perf_counter()
        for _ in range(1000):
            msgpack_data = msgpack.packb(thread_dict)
        msgpack_serialize_time = (time.perf_counter() - start_time) * 1000

        # MessagePack反序列化性能
        start_time = time.perf_counter()
        for _ in range(1000):
            msgpack.unpackb(msgpack_data, raw=False)
        msgpack_deserialize_time = (time.perf_counter() - start_time) * 1000

        # JSON序列化性能对比
        start_time = time.perf_counter()
        for _ in range(1000):
            json_data = json.dumps(thread_dict, default=str, ensure_ascii=False).encode()
        json_serialize_time = (time.perf_counter() - start_time) * 1000

        # JSON反序列化性能对比
        start_time = time.perf_counter()
        for _ in range(1000):
            json.loads(json_data.decode())
        json_deserialize_time = (time.perf_counter() - start_time) * 1000

        # 数据大小对比
        msgpack_size = len(msgpack_data)
        json_size = len(json_data)

        print(f"序列化性能对比 (1000次):")
        print(f"  MessagePack - 序列化: {msgpack_serialize_time:.2f}ms, 反序列化: {msgpack_deserialize_time:.2f}ms")
        print(f"  JSON - 序列化: {json_serialize_time:.2f}ms, 反序列化: {json_deserialize_time:.2f}ms")
        print(f"数据大小对比:")
        print(f"  MessagePack: {msgpack_size} bytes")
        print(f"  JSON: {json_size} bytes")
        print(f"  大小优化: {((json_size - msgpack_size) / json_size * 100):.1f}%")

        # 性能断言
        assert msgpack_serialize_time < json_serialize_time * 2, "MessagePack序列化不应该显著慢于JSON"
        assert msgpack_size < json_size, "MessagePack数据应该更小"


def run_performance_benchmark():
    """运行性能基准测试"""
    import pytest

    print("=" * 60)
    print("线程存储性能基准测试 (Redis + PostgreSQL)")
    print("=" * 60)
    print("运行命令: pytest tests/api/test_thread_performance.py -v -s")
    print("=" * 60)

    # 直接运行pytest
    pytest.main([
        "tests/api/test_thread_performance.py",
        "-v", "-s",
        "--tb=short"
    ])


if __name__ == "__main__":
    run_performance_benchmark()