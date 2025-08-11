"""
LLM 相关依赖
"""

from fastapi import HTTPException, Depends

from src.auth import JWTTenantContext, get_jwt_tenant_context
from src.api.schemas.llm import LLMProviderType


async def get_llm_service():
    """返回LLM管理服务（当前为简单占位实现）"""
    class MockLLMService:
        def __init__(self):
            self.providers = {}
            self.configs = {}

    return MockLLMService()


async def validate_provider_access(
    provider: LLMProviderType,
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
) -> None:
    """校验租户是否有权限访问指定LLM提供商"""
    llm_permission = f"llm.use.{provider.value.lower()}"
    if not tenant_context.has_permission(llm_permission) and not tenant_context.has_permission("llm.use.*"):
        raise HTTPException(status_code=403, detail={"error": "LLM_PROVIDER_ACCESS_DENIED", "message": f"无权访问LLM提供商 {provider.value}"})

    supported = {
        LLMProviderType.OPENAI,
        LLMProviderType.ANTHROPIC,
        LLMProviderType.GEMINI,
        LLMProviderType.DEEPSEEK,
    }
    if provider not in supported:
        raise HTTPException(status_code=400, detail={"error": "UNSUPPORTED_PROVIDER", "message": f"不支持的LLM提供商: {provider.value}"})


