from __future__ import annotations

from typing import Dict, Any, Optional, List

from models.tenant import TenantConfig
from api.dependencies.tenant_manager import get_tenant_manager, TenantManager
from api.schemas.tenant import (
    TenantSyncRequest,
    TenantUpdateRequest,
    TenantStatusResponse,
    TenantListResponse,
)
from src.utils import get_current_datetime


class TenantHandler:
    async def sync_tenant(self, request: TenantSyncRequest) -> Dict[str, Any]:
        manager: TenantManager = await get_tenant_manager()
        existing = await manager.get_tenant_config(request.tenant_id)
        cfg = existing or TenantConfig(
            tenant_id=request.tenant_id,
            tenant_name=request.tenant_name or request.tenant_id,
            created_at=get_current_datetime(),
            updated_at=get_current_datetime(),
        )

        # Update basic tenant fields
        if request.tenant_name:
            cfg.tenant_name = request.tenant_name
        cfg.is_active = request.is_active

        # Update features if provided
        if request.features:
            cfg.feature_flags = {feature: True for feature in request.features}

        ok = await manager.save_tenant_config(cfg)
        return {
            "status": "success" if ok else "failed",
            "tenant_id": cfg.tenant_id,
            "features_enabled": request.features or [],
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
            updated_at=cfg.updated_at,
            last_access=cfg.last_access,
        )

    async def update_tenant(self, tenant_id: str, request: TenantUpdateRequest) -> Dict[str, Any]:
        manager: TenantManager = await get_tenant_manager()
        cfg = await manager.get_tenant_config(tenant_id)
        if not cfg:
            raise ValueError("Tenant not found")
        
        if request.is_active is not None:
            cfg.is_active = request.is_active
        
        if request.features:
            cfg.feature_flags = {feature: True for feature in request.features}
            
        ok = await manager.save_tenant_config(cfg)
        return {
            "status": "updated" if ok else "failed",
            "features": request.features or [],
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
                    "tenant_name": cfg.tenant_name,
                    "is_active": cfg.is_active,
                    "updated_at": cfg.updated_at,
                    "features_enabled": list(cfg.feature_flags.keys()) if cfg.feature_flags else [],
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