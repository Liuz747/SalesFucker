#!/usr/bin/env python3
"""
回调测试服务器

用于测试MAS后台工作流处理器的回调功能。
该服务器接收来自BackgroundWorkflowProcessor的POST请求，
并记录、验证回调数据的格式和内容。

使用方法:
1. python test/test_callback_server.py
2. 配置 .env 文件: CALLBACK_URL=http://localhost:8001
3. 触发异步工作流请求
4. 观察服务器日志中的回调数据
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, ValidationError

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CallbackTestServer")

app = FastAPI(title="MAS Callback Test Server", version="1.0.0")

# 预期的回调数据模型（用于验证）
class WorkflowData(BaseModel):
    type: str
    content: Any

class CallbackPayload(BaseModel):
    run_id: str
    thread_id: str  
    status: str
    data: list[WorkflowData] = None
    error: str = None
    processing_time: float
    completed_at: datetime
    metadata: dict

# 存储接收到的回调记录
callback_history = []

@app.get("/")
async def root():
    """根路径 - 显示服务器状态"""
    return {
        "service": "MAS Callback Test Server",
        "status": "running",
        "callbacks_received": len(callback_history),
        "last_callback": callback_history[-1]["timestamp"] if callback_history else None
    }

@app.get("/callbacks")
async def get_callbacks():
    """获取所有接收到的回调记录"""
    return {
        "total": len(callback_history),
        "callbacks": callback_history
    }

@app.post("/api")
async def receive_callback(request: Request):
    """
    接收来自MAS BackgroundWorkflowProcessor的回调
    
    这是主要的回调端点，对应background_process.py中的callback_endpoint = "/api"
    """
    try:
        # 获取请求体
        body = await request.json()
        headers = dict(request.headers)
        
        # 记录接收时间
        received_at = datetime.now()
        
        print("=" * 60)
        print(f"🎯 回调接收时间: {received_at}")
        print(f"📡 请求头: {json.dumps(headers, indent=2)}")
        print(f"📦 回调数据:")
        print(json.dumps(body, indent=2, default=str, ensure_ascii=False))
        print("=" * 60)
        
        # 验证回调数据格式
        try:
            validated_payload = CallbackPayload(**body)
            validation_status = "✅ 数据格式验证成功"
            logger.info("回调数据格式验证成功")
        except ValidationError as e:
            validation_status = f"❌ 数据格式验证失败: {str(e)}"
            logger.error(f"回调数据格式验证失败: {e}")
        
        # 分析回调内容
        analysis = analyze_callback(body)
        
        # 保存回调记录
        callback_record = {
            "timestamp": received_at,
            "headers": headers,
            "payload": body,
            "validation_status": validation_status,
            "analysis": analysis
        }
        callback_history.append(callback_record)
        
        # 限制历史记录数量
        if len(callback_history) > 100:
            callback_history.pop(0)
        
        logger.info(f"回调处理完成 - 运行ID: {body.get('run_id', 'unknown')}")
        
        return {
            "status": "success",
            "message": "回调接收成功",
            "received_at": received_at,
            "validation": validation_status,
            "run_id": body.get("run_id"),
            "thread_id": body.get("thread_id")
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}")
        raise HTTPException(status_code=400, detail=f"JSON解析失败: {str(e)}")
    
    except Exception as e:
        logger.error(f"处理回调时发生错误: {e}")
        raise HTTPException(status_code=500, detail=f"处理回调失败: {str(e)}")

def analyze_callback(payload: Dict[str, Any]) -> Dict[str, Any]:
    """分析回调数据"""
    analysis = {
        "total_agents": 0,
        "agent_types": [],
        "status_analysis": "unknown",
        "has_error": False,
        "processing_time_analysis": "unknown"
    }
    
    try:
        # 分析智能体数据
        if "data" in payload and payload["data"]:
            analysis["total_agents"] = len(payload["data"])
            analysis["agent_types"] = [item.get("type", "unknown") for item in payload["data"]]
        
        # 分析状态
        status = payload.get("status", "unknown")
        if status == "completed":
            analysis["status_analysis"] = "✅ 工作流成功完成"
        elif status == "failed":
            analysis["status_analysis"] = "❌ 工作流处理失败"
        else:
            analysis["status_analysis"] = f"⚠️ 未知状态: {status}"
        
        # 检查错误信息
        analysis["has_error"] = "error" in payload and payload["error"] is not None
        
        # 分析处理时间
        processing_time = payload.get("processing_time", 0)
        if processing_time < 1000:
            analysis["processing_time_analysis"] = f"⚡ 快速处理: {processing_time:.1f}ms"
        elif processing_time < 5000:
            analysis["processing_time_analysis"] = f"🟡 正常处理: {processing_time:.1f}ms"
        else:
            analysis["processing_time_analysis"] = f"🔴 处理较慢: {processing_time:.1f}ms"
            
    except Exception as e:
        logger.error(f"分析回调数据失败: {e}")
        analysis["error"] = str(e)
    
    return analysis

@app.delete("/callbacks")
async def clear_callbacks():
    """清空回调历史记录"""
    global callback_history
    count = len(callback_history)
    callback_history.clear()
    return {"message": f"已清空 {count} 条回调记录"}

if __name__ == "__main__":
    print("🚀 启动MAS回调测试服务器...")
    print("📍 回调端点: http://localhost:8001/api")
    print("📊 状态查看: http://localhost:8001/")
    print("📜 回调历史: http://localhost:8001/callbacks")
    print("🧹 清空历史: DELETE http://localhost:8001/callbacks")
    print("-" * 50)
    print("配置说明:")
    print("在 .env 文件中设置: CALLBACK_URL=http://localhost:8001")
    print("然后重启 MAS 应用程序以应用配置")
    print("-" * 50)
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8001,
        log_level="info",
        reload=False
    )