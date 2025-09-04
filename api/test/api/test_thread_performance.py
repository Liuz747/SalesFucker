"""
线程存储性能测试

测试Redis+PostgreSQL二级存储架构的性能特征。
MessagePack序列化 + 异步数据库写入优化。
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch, MagicMock

from controllers.workspace.conversation.schema import Thread, ThreadMetadata
from repositories.thread_repository import ThreadRepository


class TestThreadPerformance:
    """线程存储性能测试类"""
    
    @pytest.fixture
    async def mock_repository(self):
        """模拟存储库fixture"""
        repo = ThreadRepository()
        
        # 模拟Redis客户端
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock(return_value=True)
        
        with patch('repositories.thread_repository.get_redis_client', return_value=mock_redis):
            await repo.initialize()
            yield repo
            await repo.cleanup()
    
    @pytest.fixture
    def sample_thread(self):
        """示例线程fixture"""
        return Thread(
            thread_id="test-thread-123",
            assistant_id="assistant-456", 
            metadata=ThreadMetadata(tenant_id="tenant-789")
        )
    
    @pytest.mark.asyncio
    async def test_redis_cache_performance(self, mock_repository, sample_thread):
        """测试Redis缓存性能"""
        # 性能测试 - 写入
        start_time = time.perf_counter()
        await mock_repository.create_thread(sample_thread)
        write_time = (time.perf_counter() - start_time) * 1000  # 转换为毫秒
        
        # 模拟Redis返回MessagePack数据
        import msgpack
        thread_dict = sample_thread.model_dump()
        thread_dict["created_at"] = sample_thread.created_at.isoformat()
        thread_dict["updated_at"] = sample_thread.updated_at.isoformat()
        mock_repository._redis_client.get.return_value = msgpack.packb(thread_dict)
        
        # 性能测试 - 读取
        start_time = time.perf_counter()
        cached_thread = await mock_repository.get_thread(sample_thread.thread_id)
        read_time = (time.perf_counter() - start_time) * 1000
        
        # 断言性能指标
        assert write_time < 10.0, f"Redis写入耗时过长: {write_time:.2f}ms (目标: < 10ms)"
        assert read_time < 15.0, f"Redis读取耗时过长: {read_time:.2f}ms (目标: < 15ms)"
        assert cached_thread is not None
        assert cached_thread.thread_id == sample_thread.thread_id
        
        print(f"Redis缓存性能 - 写入: {write_time:.2f}ms, 读取: {read_time:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_performance(self, mock_repository):
        """测试并发操作性能"""
        # 创建50个测试线程
        threads = []
        for i in range(50):
            thread = Thread(
                thread_id=f"concurrent-test-{i}",
                assistant_id=f"assistant-{i}",
                metadata=ThreadMetadata(tenant_id="tenant-concurrent")
            )
            threads.append(thread)
        
        # 并发写入性能测试
        start_time = time.perf_counter()
        tasks = [mock_repository.create_thread(thread) for thread in threads]
        await asyncio.gather(*tasks)
        write_time = (time.perf_counter() - start_time) * 1000
        
        # 模拟Redis返回数据用于读取测试
        import msgpack
        
        def mock_get_side_effect(key):
            thread_id = key.replace("thread:", "")
            for thread in threads:
                if thread.thread_id == thread_id:
                    thread_dict = thread.model_dump()
                    thread_dict["created_at"] = thread.created_at.isoformat()
                    thread_dict["updated_at"] = thread.updated_at.isoformat()
                    return msgpack.packb(thread_dict)
            return None
        
        mock_repository._redis_client.get.side_effect = mock_get_side_effect
        
        # 并发读取性能测试
        start_time = time.perf_counter()
        read_tasks = [mock_repository.get_thread(f"concurrent-test-{i}") for i in range(50)]
        results = await asyncio.gather(*read_tasks)
        read_time = (time.perf_counter() - start_time) * 1000
        
        # 性能断言
        avg_write_time = write_time / 50
        avg_read_time = read_time / 50
        
        assert avg_write_time < 20.0, f"平均写入耗时过长: {avg_write_time:.2f}ms (目标: < 20ms)"
        assert avg_read_time < 10.0, f"平均读取耗时过长: {avg_read_time:.2f}ms (目标: < 10ms)"
        assert len([r for r in results if r is not None]) == 50
        
        print(f"并发操作性能 - 平均写入: {avg_write_time:.2f}ms, 平均读取: {avg_read_time:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_messagepack_serialization_performance(self, sample_thread):
        """测试MessagePack序列化性能"""
        import json
        import msgpack
        
        thread_dict = sample_thread.model_dump()
        thread_dict["created_at"] = sample_thread.created_at.isoformat()
        thread_dict["updated_at"] = sample_thread.updated_at.isoformat()
        
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
            json_data = json.dumps(thread_dict, ensure_ascii=False).encode()
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
        assert msgpack_serialize_time < json_serialize_time, "MessagePack序列化应该更快"
        assert msgpack_deserialize_time < json_deserialize_time, "MessagePack反序列化应该更快"
        assert msgpack_size < json_size, "MessagePack数据应该更小"
    
    @pytest.mark.asyncio
    async def test_database_fallback_performance(self, mock_repository, sample_thread):
        """测试数据库回退性能"""
        # 模拟Redis缓存未命中
        mock_repository._redis_client.get.return_value = None
        
        # 模拟数据库查询
        with patch('services.thread_service.ThreadService.query', return_value=sample_thread) as mock_query:
            start_time = time.perf_counter()
            result = await mock_repository.get_thread(sample_thread.thread_id)
            fallback_time = (time.perf_counter() - start_time) * 1000
            
            # 验证回退逻辑
            assert result is not None
            assert result.thread_id == sample_thread.thread_id
            mock_query.assert_called_once_with(sample_thread.thread_id)
            
            # 验证性能
            assert fallback_time < 50.0, f"数据库回退耗时过长: {fallback_time:.2f}ms (目标: < 50ms)"
            
            print(f"数据库回退性能: {fallback_time:.2f}ms")


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