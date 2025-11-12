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

from config import mas_config
from controllers.middleware import SafetyInterceptor, JWTMiddleware
from controllers import app_router, __version__
from libs.factory import infra_registry
from schemas.exceptions import BaseHTTPException
from utils import get_component_logger, configure_logging, to_isoformat

# 配置日志
logger = get_component_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    configure_logging()
    await infra_registry.create_clients()
    await infra_registry.test_clients()
    
    yield
    # 关闭时执行
    await infra_registry.shutdown_clients()


# 创建FastAPI应用
app = FastAPI(
    title="MAS营销智能体系统API",
    description="多智能体营销系统的RESTful API",
    version=__version__,
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

# 全局异常处理
@app.exception_handler(BaseHTTPException)
async def api_exception_handler(_, exc: BaseHTTPException):
    """处理自定义API异常"""
    return JSONResponse(
        status_code=exc.http_status_code,
        content={
            **exc.data,
            "timestamp": to_isoformat()
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
app.include_router(app_router, prefix="/v1")

# 根路径健康检查
@app.get("/")
async def root():
    """根路径健康检查"""
    return {
        "service": mas_config.APP_NAME,
        "status": "运行中",
        "version": __version__,
        "docs": "/docs"
    }


def main():
    """Main entry point for the application."""
    uvicorn.run(
        "main:app",
        host=mas_config.APP_HOST,
        port=mas_config.APP_PORT,
        reload=mas_config.DEBUG,
        log_level=mas_config.LOG_LEVEL.lower()
    )


if __name__ == "__main__":
    main()
