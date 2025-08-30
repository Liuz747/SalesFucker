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

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.middleware import (
    SafetyInterceptor,
    TenantIsolation,
    JWTMiddleware
)
from api.endpoints import (
    agents_router,
    multimodal_router,
    assistants_router,
    prompts_router,
)
from api import (
    auth_router,
    conversations_router,
    completion_router,
    health_router,
    tenant_router,
)
from api.exceptions import APIException
from config import mas_config
from utils import get_component_logger, configure_logging
from repositories.thread_repository import get_thread_repository

# 配置日志
logger = get_component_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    configure_logging()
    repository = await get_thread_repository()
    
    yield
    # 关闭时执行
    repository = await get_thread_repository()
    await repository.cleanup()


# 创建FastAPI应用
app = FastAPI(
    title="MAS营销智能体系统API",
    description="多智能体营销系统的RESTful API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加自定义中间件 (order matters - JWT first for security)
app.add_middleware(JWTMiddleware, exclude_paths=[
    "/",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/v1/health",
    "/v1/auth/token"
], exclude_prefixes=[
    "/static/",
    "/assets/"
])
app.add_middleware(SafetyInterceptor)
app.add_middleware(TenantIsolation)

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
app.include_router(health_router, prefix="/v1")
app.include_router(auth_router, prefix="/v1")
app.include_router(agents_router, prefix="/v1")
app.include_router(conversations_router, prefix="/v1")
app.include_router(multimodal_router, prefix="/v1")
app.include_router(assistants_router, prefix="/v1")
app.include_router(prompts_router, prefix="/v1")
app.include_router(tenant_router, prefix="/v1")
app.include_router(completion_router, prefix="/v1")

# 根路径健康检查
@app.get("/")
async def root():
    """根路径健康检查"""
    return {
        "service": mas_config.APP_NAME,
        "status": "运行中",
        "version": "0.2.0",
        "docs": "/docs"
    }


def main():
    """Main entry point for the application."""
    uvicorn.run(
        "main:app",
        host=mas_config.APP_HOST,
        port=mas_config.APP_PORT,
        reload=mas_config.DEBUG,
        log_level="info" if not mas_config.DEBUG else "debug"
    )


if __name__ == "__main__":
    main()