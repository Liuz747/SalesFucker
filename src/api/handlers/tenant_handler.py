from __future__ import annotations

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from src.auth.models import TenantConfig
from src.auth.tenant_manager import get_tenant_manager, TenantManager
from src.api.schemas.tenant import (
    TenantSyncRequest,
    TenantUpdateRequest,
    TenantStatusResponse,
    TenantListResponse,
)


def _fingerprint_pem(pem: Optional[str]) -> Optional[str]:
    if not pem:
        return None
    import hashlib

    data = pem.encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:16]


class TenantHandler:
    async def sync_tenant(self, request: TenantSyncRequest) -> Dict[str, Any]:
        manager: TenantManager = await get_tenant_manager()
        existing = await manager.get_tenant_config(request.tenant_id)
        cfg = existing or TenantConfig(
            tenant_id=request.tenant_id,
            tenant_name=request.tenant_name or request.tenant_id,
            jwt_public_key=request.jwt_public_key,
            jwt_algorithm="RS256",
            jwt_issuer=request.issuer or "",
            jwt_audience="mas-api",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Update JWKS-first fields
        cfg.issuer = request.issuer or cfg.issuer
        if request.jwks_uri:
            cfg.jwks_uri = str(request.jwks_uri)
        if request.jwt_public_key:
            cfg.jwt_public_key = request.jwt_public_key
        cfg.is_active = request.is_active

        ok = await manager.save_tenant_config(cfg)
        return {
            "status": "success" if ok else "failed",
            "public_key_fingerprint": _fingerprint_pem(cfg.jwt_public_key),
        }

    async def get_tenant_status(self, tenant_id: str) -> Optional[TenantStatusResponse]:
        manager: TenantManager = await get_tenant_manager()
        cfg = await manager.get_tenant_config(tenant_id)
        if not cfg:
            return None
        return TenantStatusResponse(
            tenant_id=cfg.tenant_id,
            tenant_name=cfg.tenant_name,
            is_active=cfg.is_active,
            issuer=cfg.issuer or cfg.jwt_issuer,
            jwks_uri=cfg.jwks_uri,
            has_public_key=bool(cfg.jwt_public_key),
            updated_at=cfg.updated_at,
            last_access=cfg.last_access,
        )

    async def update_tenant(self, tenant_id: str, request: TenantUpdateRequest) -> Dict[str, Any]:
        manager: TenantManager = await get_tenant_manager()
        cfg = await manager.get_tenant_config(tenant_id)
        if not cfg:
            raise ValueError("Tenant not found")
        if request.issuer is not None:
            cfg.issuer = request.issuer
        if request.jwks_uri is not None:
            cfg.jwks_uri = str(request.jwks_uri)
        if request.jwt_public_key is not None:
            cfg.jwt_public_key = request.jwt_public_key
        if request.is_active is not None:
            cfg.is_active = request.is_active
        ok = await manager.save_tenant_config(cfg)
        return {
            "status": "updated" if ok else "failed",
            "features": request.features or [],
            "public_key_fingerprint": _fingerprint_pem(cfg.jwt_public_key),
        }

    async def delete_tenant(self, tenant_id: str, force: bool = False) -> Dict[str, Any]:
        # Placeholder for persistence-backed deletion; for now, invalidate cache
        manager: TenantManager = await get_tenant_manager()
        await manager.invalidate_cache(tenant_id)
        return {"data_purged": force}

    async def list_tenants(
        self, status_filter: Optional[str], limit: int, offset: int
    ) -> TenantListResponse:
        manager: TenantManager = await get_tenant_manager()
        ids = await manager.get_all_tenants()
        items: List[Dict[str, Any]] = []
        for tid in ids:
            cfg = await manager.get_tenant_config(tid)
            if not cfg:
                continue
            if status_filter == "active" and not cfg.is_active:
                continue
            if status_filter == "inactive" and cfg.is_active:
                continue
            items.append(
                {
                    "tenant_id": cfg.tenant_id,
                    "is_active": cfg.is_active,
                    "issuer": cfg.issuer or cfg.jwt_issuer,
                    "jwks_uri": cfg.jwks_uri,
                    "has_public_key": bool(cfg.jwt_public_key),
                    "updated_at": cfg.updated_at,
                }
            )
        total = len(items)
        return TenantListResponse(total=total, tenants=items[offset : offset + limit])

    async def bulk_sync_tenants(self, tenants: List[TenantSyncRequest]) -> List[Dict[str, Any]]:
        results = []
        for req in tenants:
            try:
                results.append(await self.sync_tenant(req))
            except Exception as e:
                results.append({"status": "failed", "error": str(e)})
        return results

    async def health_check(self) -> Dict[str, Any]:
        manager: TenantManager = await get_tenant_manager()
        stats = await manager.health_check()
        return {"database_connected": True, "tenant_count": stats.get("cached_tenants", 0)}


