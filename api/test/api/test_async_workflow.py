#!/usr/bin/env python3
"""
异步工作流测试脚本

用于测试MAS异步工作流端点和回调功能的便捷测试脚本。

使用方法:
1. 启动回调测试服务器: python test/test_callback_server.py
2. 配置环境变量
3. 运行此测试脚本: python test/test_async_workflow.py
"""

import asyncio
import uuid
from typing import Optional

import httpx


class AsyncWorkflowTester:
    """异步工作流测试器"""
    
    def __init__(
        self, 
        base_url: str = "http://localhost:8000",
        auth_token: Optional[str] = None
    ):
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        
    def _get_headers(self) -> dict:
        """获取请求头"""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers
    
    async def create_test_thread(self, tenant_id: Optional[str] = None) -> dict:
        """创建测试线程"""
        if not tenant_id:
            tenant_id = str(uuid.uuid4())
            
        payload = {
            "metadata": {
                "tenant_id": tenant_id
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/v1/threads",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    thread_data = response.json()
                    print(f"✅ 测试线程创建成功: {thread_data['thread_id']}")
                    return thread_data
                else:
                    print(f"❌ 线程创建失败: {response.status_code} - {response.text}")
                    return None
                    
            except Exception as e:
                print(f"❌ 创建线程时发生错误: {e}")
                return None
    
    async def trigger_async_workflow(
        self, 
        thread_id: str, 
        message: str = "测试异步工作流和回调功能",
        assistant_id: Optional[str] = None
    ) -> dict:
        """触发异步工作流"""
        if not assistant_id:
            assistant_id = str(uuid.uuid4())
            
        payload = {
            "assistant_id": assistant_id,
            "input": {
                "role": "user",
                "content": message
            },
            "metadata": {}
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/threads/{thread_id}/async",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    run_data = response.json()
                    print(f"✅ 异步工作流启动成功:")
                    print(f"   📋 运行ID: {run_data['run_id']}")
                    print(f"   🧵 线程ID: {run_data['thread_id']}")
                    print(f"   📊 状态: {run_data['status']}")
                    return run_data
                else:
                    print(f"❌ 异步工作流启动失败: {response.status_code} - {response.text}")
                    return None
                    
            except Exception as e:
                print(f"❌ 触发异步工作流时发生错误: {e}")
                return None
    
    async def check_callback_server(self, callback_url: str = "http://localhost:8001") -> bool:
        """检查回调测试服务器状态"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{callback_url}/",
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    status_data = response.json()
                    print(f"✅ 回调测试服务器运行正常:")
                    print(f"   📡 服务: {status_data['service']}")
                    print(f"   📊 状态: {status_data['status']}")
                    print(f"   📨 已接收回调: {status_data['callbacks_received']}")
                    return True
                else:
                    print(f"❌ 回调服务器响应异常: {response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"❌ 无法连接回调测试服务器: {e}")
                print("请确保回调测试服务器正在运行: python test/test_callback_server.py")
                return False


async def main():
    """主测试流程"""
    print("🧪 MAS异步工作流和回调功能测试")
    print("=" * 50)
    
    # 初始化测试器
    tester = AsyncWorkflowTester()
    
    # 检查回调服务器
    print("1️⃣ 检查回调测试服务器状态...")
    callback_ok = await tester.check_callback_server()
    if not callback_ok:
        print("\n⚠️  请先启动回调测试服务器:")
        print("   python test/test_callback_server.py")
        return
    
    print("\n2️⃣ 创建测试线程...")
    thread_data = await tester.create_test_thread()
    if not thread_data:
        print("❌ 无法创建测试线程，测试终止")
        return
    
    thread_id = thread_data["thread_id"]
    
    print("\n3️⃣ 触发异步工作流...")
    run_data = await tester.trigger_async_workflow(
        thread_id=thread_id,
        message="你好，我想了解一些护肤产品推荐，特别是适合干性皮肤的产品。"
    )
    
    if not run_data:
        print("❌ 无法启动异步工作流，测试终止")
        return
    
    print("\n4️⃣ 等待后台处理和回调...")
    print("🔄 工作流正在后台处理中，请观察回调测试服务器的日志输出")
    print("📍 回调服务器地址: http://localhost:8001")
    print("📊 查看回调状态: http://localhost:8001/callbacks")
    
    # 等待一段时间让用户观察
    print("\n⏳ 等待10秒以观察回调...")
    await asyncio.sleep(10)
    
    # 检查回调服务器是否收到数据
    print("\n5️⃣ 检查回调接收情况...")
    await tester.check_callback_server()
    
    print("\n✅ 测试完成！")
    print("💡 提示:")
    print("   - 如果未收到回调，请检查 .env 文件中的 CALLBACK_URL 配置")
    print("   - 确保配置为: CALLBACK_URL=http://localhost:8001")
    print("   - 重启MAS应用程序以应用新的回调URL配置")


if __name__ == "__main__":
    asyncio.run(main())