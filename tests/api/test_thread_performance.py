"""
线程存储性能测试

测试混合存储策略的性能特征，验证云端PostgreSQL优化效果。
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch

from api.workspace.conversation.schema import ThreadModel, ThreadMetadata
from repositories.thread_repository import ThreadRepository


class TestThreadPerformance:
    """线程存储性能测试类"""
    
    @pytest.fixture
    async def mock_repository(self):
        """模拟存储库fixture"""
        repo = ThreadRepository()
        
        # 模拟数据库连接
        with patch('repositories.thread_repository.database_session'), \
             patch('repositories.thread_repository.get_redis_client_async'):
            await repo.initialize()
            yield repo
            await repo.cleanup()
    
    @pytest.fixture
    def sample_thread(self):
        """示例线程fixture"""
        return ThreadModel(
            thread_id="test-thread-123",
            assistant_id="assistant-456", 
            metadata=ThreadMetadata(tenant_id="tenant-789")
        )
    
    async def test_memory_cache_performance(self):
        """测试内存缓存性能"""
        cache_manager = ThreadCacheManager()
        await cache_manager.initialize()
        
        # 创建测试线程
        thread = ThreadModel(
            thread_id="perf-test-1",
            assistant_id="assistant-1",
            metadata=ThreadMetadata(tenant_id="tenant-1")
        )
        
        # 性能测试 - 写入
        start_time = time.perf_counter()
        await cache_manager.set_thread(thread)
        write_time = (time.perf_counter() - start_time) * 1000  # 转换为毫秒
        
        # 性能测试 - 读取
        start_time = time.perf_counter()
        cached_thread = await cache_manager.get_thread("perf-test-1")
        read_time = (time.perf_counter() - start_time) * 1000
        
        # 断言性能指标
        assert write_time < 5.0, f"缓存写入耗时过长: {write_time:.2f}ms (目标: < 5ms)"
        assert read_time < 1.0, f"缓存读取耗时过长: {read_time:.2f}ms (目标: < 1ms)"
        assert cached_thread is not None
        assert cached_thread.thread_id == "perf-test-1"
        
        print(f"内存缓存性能 - 写入: {write_time:.2f}ms, 读取: {read_time:.2f}ms")
    
    async def test_batch_operations_performance(self):
        """测试批量操作性能"""
        cache_manager = ThreadCacheManager()
        await cache_manager.initialize()
        
        # 创建100个测试线程
        threads = []
        for i in range(100):
            thread = ThreadModel(
                thread_id=f"batch-test-{i}",
                assistant_id=f"assistant-{i}",
                metadata=ThreadMetadata(tenant_id="tenant-batch")
            )
            threads.append(thread)
        
        # 批量写入性能测试
        start_time = time.perf_counter()
        for thread in threads:
            await cache_manager.set_thread(thread)
        write_time = (time.perf_counter() - start_time) * 1000
        
        # 批量读取性能测试
        thread_ids = [f"batch-test-{i}" for i in range(100)]
        start_time = time.perf_counter()
        results = await cache_manager.batch_get_threads(thread_ids)
        read_time = (time.perf_counter() - start_time) * 1000
        
        # 性能断言
        avg_write_time = write_time / 100
        avg_read_time = read_time / 100
        
        assert avg_write_time < 10.0, f"平均写入耗时过长: {avg_write_time:.2f}ms (目标: < 10ms)"
        assert avg_read_time < 5.0, f"平均读取耗时过长: {avg_read_time:.2f}ms (目标: < 5ms)"
        assert len(results) == 100
        
        print(f"批量操作性能 - 平均写入: {avg_write_time:.2f}ms, 平均读取: {avg_read_time:.2f}ms")
    
    async def test_cache_hit_rate(self):
        """测试缓存命中率"""
        cache_manager = ThreadCacheManager()
        await cache_manager.initialize()
        
        # 写入测试数据
        threads = []
        for i in range(50):
            thread = ThreadModel(
                thread_id=f"hit-rate-test-{i}",
                assistant_id=f"assistant-{i}",
                metadata=ThreadMetadata(tenant_id="tenant-hit-rate")
            )
            threads.append(thread)
            await cache_manager.set_thread(thread)
        
        # 执行多次读取操作
        for _ in range(3):  # 读取3轮，应该都命中缓存
            for i in range(50):
                thread = await cache_manager.get_thread(f"hit-rate-test-{i}")
                assert thread is not None
        
        # 检查缓存统计
        stats = cache_manager.get_cache_stats()
        cache_hit_rate = stats["cache_hit_rate"]
        
        assert cache_hit_rate > 90.0, f"缓存命中率过低: {cache_hit_rate:.1f}% (目标: > 90%)"
        
        print(f"缓存命中率: {cache_hit_rate:.1f}%")
        print(f"内存命中: {stats['performance_stats']['memory_hits']}")
        print(f"Redis命中: {stats['performance_stats']['redis_hits']}")
        print(f"缓存未命中: {stats['performance_stats']['cache_misses']}")
    
    @pytest.mark.asyncio
    async def test_concurrent_access_performance(self):
        """测试并发访问性能"""
        cache_manager = ThreadCacheManager()
        await cache_manager.initialize()
        
        async def create_and_access_thread(thread_id: str):
            """创建并访问线程"""
            thread = ThreadModel(
                thread_id=thread_id,
                assistant_id=f"assistant-{thread_id}",
                metadata=ThreadMetadata(tenant_id="tenant-concurrent")
            )
            
            # 写入
            await cache_manager.set_thread(thread)
            
            # 多次读取
            for _ in range(5):
                result = await cache_manager.get_thread(thread_id)
                assert result is not None
        
        # 并发测试 - 50个并发任务
        start_time = time.perf_counter()
        tasks = [
            create_and_access_thread(f"concurrent-{i}") 
            for i in range(50)
        ]
        await asyncio.gather(*tasks)
        total_time = (time.perf_counter() - start_time) * 1000
        
        # 性能断言
        avg_time_per_task = total_time / 50
        assert avg_time_per_task < 100.0, f"并发任务平均耗时过长: {avg_time_per_task:.2f}ms"
        
        print(f"并发访问性能 - 50个任务总耗时: {total_time:.2f}ms, 平均: {avg_time_per_task:.2f}ms")


def run_performance_benchmark():
    """运行性能基准测试"""
    async def benchmark():
        test_instance = TestThreadPerformance()
        
        print("=" * 60)
        print("线程存储性能基准测试")
        print("=" * 60)
        
        print("\n1. 内存缓存性能测试:")
        await test_instance.test_memory_cache_performance()
        
        print("\n2. 批量操作性能测试:")
        await test_instance.test_batch_operations_performance()
        
        print("\n3. 缓存命中率测试:")
        await test_instance.test_cache_hit_rate()
        
        print("\n4. 并发访问性能测试:")
        await test_instance.test_concurrent_access_performance()
        
        print("\n" + "=" * 60)
        print("性能基准测试完成")
        print("=" * 60)
    
    asyncio.run(benchmark())


if __name__ == "__main__":
    run_performance_benchmark()