"""
FastAPI主应用入口

该模块是整个API服务的入口点，负责创建FastAPI应用实例、
注册路由器、配置中间件和异常处理。

核心功能:
- FastAPI应用初始化
- 路由器注册和管理
- 中间件配置
- 全局异常处理
- API文档配置
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from .exceptions import APIException
from .middleware.safety_interceptor import SafetyInterceptorMiddleware
from .middleware.tenant_isolation import TenantIsolationMiddleware
from .endpoints import (
    agents_router,
    conversations_router,
    llm_management_router,
    multimodal_router,
    health_router
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="MAS化妆品智能体系统API",
    description="多智能体化妆品营销系统的RESTful API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加自定义中间件
app.add_middleware(SafetyInterceptorMiddleware)
app.add_middleware(TenantIsolationMiddleware)

# 全局异常处理
@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    """处理自定义API异常"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details
            },
            "timestamp": exc.timestamp.isoformat(),
            "path": str(request.url)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """处理未捕获的异常"""
    logger.error(f"未捕获异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "服务器内部错误",
                "details": None
            },
            "timestamp": None,
            "path": str(request.url)
        }
    )

# 注册路由器
app.include_router(health_router, prefix="/api/v1")
app.include_router(agents_router, prefix="/api/v1")
app.include_router(conversations_router, prefix="/api/v1")
app.include_router(llm_management_router, prefix="/api/v1")
app.include_router(multimodal_router, prefix="/api/v1")

# 根路径健康检查
@app.get("/")
async def root():
    """根路径健康检查"""
    return {
        "service": "MAS化妆品智能体系统",
        "status": "运行中",
        "version": "1.0.0",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)