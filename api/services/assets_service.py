"""
素材服务模块

负责从外部数据库查询素材信息，并提供Redis缓存支持。
支持基于关键词的智能搜索和排序。
"""

import json
from typing import Any, Optional
from uuid import UUID

from libs.factory import infra_registry
from utils import get_component_logger, ExternalClient

logger = get_component_logger(__name__, "AssetsService")


class AssetsService:
    """
    素材服务类

    提供素材查询功能，从外部数据库获取素材信息。
    支持Redis缓存，按租户隔离，缓存有效期1天。
    """

    def __init__(self, base_url: Optional[str] = None):
        """
        初始化素材服务

        参数:
            base_url: 外部素材数据库的基础URL
        """
        self.base_url = base_url
        self.client = ExternalClient(base_url=base_url)

    @staticmethod
    def _get_cache_key(tenant_id: str) -> str:
        """生成缓存键"""
        return f"assets:{tenant_id}"

    async def get_cached_assets(self, tenant_id: str) -> Optional[dict[str, Any]]:
        """
        从缓存获取素材数据

        参数:
            tenant_id: 租户ID

        返回:
            Optional[dict]: 素材数据，如果不存在返回None
        """
        try:
            redis = infra_registry.get_cached_clients().redis
            cache_key = self._get_cache_key(tenant_id)

            cached_data = await redis.get(cache_key)

            if cached_data:
                assets_data = json.loads(cached_data)
                logger.info(f"从缓存获取素材: tenant_id={tenant_id}, count={len(assets_data.get('assets', []))}")
                return assets_data

            return None

        except Exception as e:
            logger.error(f"获取缓存失败: {e}", exc_info=True)
            return None

    async def set_cached_assets(self, tenant_id: str, assets_data: dict[str, Any]) -> bool:
        """
        设置素材数据到缓存

        参数:
            tenant_id: 租户ID
            assets_data: 素材数据

        返回:
            bool: 是否设置成功
        """
        try:
            redis = infra_registry.get_cached_clients().redis
            cache_key = self._get_cache_key(tenant_id)

            cached_value = json.dumps(assets_data, ensure_ascii=False)
            await redis.set(cache_key, cached_value, ex=86400)

            logger.info(
                f"素材已缓存: tenant_id={tenant_id}, "
                f"count={len(assets_data.get('assets', []))}"
            )
            return True

        except Exception as e:
            logger.error(f"设置缓存失败: {e}", exc_info=True)
            return False

    async def query_assets(
        self,
        tenant_id: str,
        thread_id: UUID,
        assistant_id: UUID,
        workflow_id: UUID,
        use_cache: bool = True,
        asset_type: int = 0,
        page: int = 1,
        limit: int = 10000
    ) -> dict[str, Any]:
        """
        查询素材数据（支持缓存）

        参数:
            tenant_id: 租户ID
            thread_id: 线程ID
            assistant_id: 助手ID
            workflow_id: 工作流ID
            use_cache: 是否使用缓存（默认True）
            asset_type: 素材类型
            page: 页码
            limit: 返回素材数量限制

        返回:
            dict: 查询结果
        """
        # 1. 尝试从缓存获取
        if use_cache:
            cached_data = await self.get_cached_assets(tenant_id)
            if cached_data:
                cached_data["from_cache"] = True
                return cached_data

        # 2. 缓存未命中，查询外部API
        try:
            request_body = {
                "reqId": str(workflow_id),
                "graphId": tenant_id,
                "assistantId": str(assistant_id),
                "threadId": str(thread_id),
                "page": page,
                "limit": limit,
                "type": asset_type,
                "flag": 0
            }

            logger.info(f"查询素材: tenant_id={tenant_id}")

            response = await self.client.make_request(
                method="POST",
                endpoint="/chat/ai/hook/queryMaterialPage",
                data=request_body,
                timeout=30.0,
                max_retries=2
            )

            # 3. 解析响应
            if isinstance(response, dict) and response.get("code") == 200:
                raw_assets = response.get("data", [])
                total = response.get("total", len(raw_assets))

                # 提取关键字段：id, name, content, remark
                assets = []
                for asset in raw_assets:
                    assets.append({
                        "id": asset.get("id"),
                        "name": asset.get("name", ""),
                        "content": asset.get("content", ""),
                        "remark": asset.get("remark", "")
                    })

                logger.info(f"素材查询成功: 返回{len(assets)}个素材 (总计{total}个)")

                assets_data = {
                    "assets": assets,
                    "total": total,
                    "from_cache": False
                }

                # 4. 存入缓存
                if use_cache:
                    await self.set_cached_assets(tenant_id, assets_data)

                return assets_data

            else:
                error_msg = response.get("msg", "Unknown error") if isinstance(response, dict) else "Invalid response"
                logger.warning(f"素材查询失败: {error_msg}")
                return {
                    "assets": [],
                    "total": 0,
                    "from_cache": False,
                    "error": error_msg
                }

        except Exception as e:
            logger.error(f"素材查询失败: {e}", exc_info=True)
            return {
                "assets": [],
                "total": 0,
                "from_cache": False,
                "error": str(e)
            }

    @staticmethod
    def search_assets(
        assets_data: dict[str, Any],
        keywords: list[str],
        top_k: int = 1,
        score_threshold: float = 0.0
    ) -> list[dict[str, Any]]:
        """
        基于关键词搜索素材

        参数:
            assets_data: 素材数据字典
            keywords: 关键词列表
            top_k: 返回前K个结果（默认10）
            score_threshold: 最低分数阈值（默认0.0）

        返回:
            list[dict]: 排序后的素材列表，每个素材包含score字段
        """
        assets = assets_data.get("assets", [])
        if not assets:
            return []

        scored_assets = []

        for asset in assets:
            # 构建可搜索文本（name, content, remark）
            searchable_text = " ".join([
                str(asset.get("name") or ""),
                str(asset.get("content") or ""),
                str(asset.get("remark") or "")
            ]).lower()

            # 计算匹配分数
            score = 0
            matched_keywords = []

            for keyword in keywords:
                keyword_lower = keyword.lower()

                # 完全匹配：+3分
                if keyword_lower in searchable_text:
                    # 在name中匹配：额外+2分
                    name_str = str(asset.get("name") or "").lower()
                    content_str = str(asset.get("content") or "").lower()

                    if keyword_lower in name_str:
                        score += 5
                        matched_keywords.append(f"{keyword}(name)")
                    # 在content中匹配：额外+1分
                    elif keyword_lower in content_str:
                        score += 4
                        matched_keywords.append(f"{keyword}(content)")
                    # 在remark中匹配：+3分
                    else:
                        score += 3
                        matched_keywords.append(f"{keyword}(remark)")

            # 只保留有匹配的素材
            if score > score_threshold:
                asset_with_score = asset.copy()
                asset_with_score["search_score"] = score
                asset_with_score["matched_keywords"] = matched_keywords
                scored_assets.append(asset_with_score)

        # 按分数降序排序
        scored_assets.sort(key=lambda x: x["search_score"], reverse=True)

        # 返回前top_k个结果
        top_assets = scored_assets[:top_k]

        logger.info(
            f"关键词搜索完成: keywords={keywords}, "
            f"匹配={len(scored_assets)}个, "
            f"返回={len(top_assets)}个"
        )

        return top_assets
