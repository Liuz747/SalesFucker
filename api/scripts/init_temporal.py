import asyncio
import sys
from datetime import timedelta
from pathlib import Path

# 添加项目根目录到 Python 路径，以便导入 config
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from temporalio.client import Client
from temporalio.service import RPCError, RPCStatusCode
# 导入 gRPC 请求对象
from temporalio.api.workflowservice.v1 import RegisterNamespaceRequest

from config import mas_config

async def init_temporal():
    """初始化 Temporal 命名空间"""
    target_host = mas_config.temporal_url
    target_namespace = mas_config.TEMPORAL_NAMESPACE
    
    print(f"正在连接 Temporal 服务器: {target_host}")
    
    try:
        # 连接 Temporal
        client = await Client.connect(target_host)
        
        print(f"正在检查/注册命名空间: {target_namespace}")
        
        try:
            # 构造注册请求
            request = RegisterNamespaceRequest(
                namespace=target_namespace,
                workflow_execution_retention_period=timedelta(days=3) # 设置数据保留期为3天
            )
            
            await client.workflow_service.register_namespace(request)
            print(f"✅ 成功注册命名空间: {target_namespace}")
            
        except RPCError as e:
            if e.status == RPCStatusCode.ALREADY_EXISTS:
                print(f"ℹ️ 命名空间已存在: {target_namespace}")
            else:
                print(f"❌ 注册命名空间失败: {e}")
                # 打印更多详细信息以便调试
                print(f"Detail: {e.details}")
                raise

    except Exception as e:
        print(f"❌ 操作失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(init_temporal())
