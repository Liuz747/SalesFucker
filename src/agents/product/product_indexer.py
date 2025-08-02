"""
产品索引管理器
Product Indexer Manager

管理产品数据的索引和RAG系统统计信息
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from src.rag import ProductIndexer

logger = logging.getLogger(__name__)

class ProductIndexManager:
    """产品索引管理器"""
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.indexer = ProductIndexer(tenant_id)
        self.logger = logging.getLogger(f"{__name__}.{tenant_id}")
        self.initialized = False
    
    async def initialize(self) -> None:
        """初始化产品索引管理器"""
        try:
            await self.indexer.initialize()
            self.initialized = True
            self.logger.info(f"产品索引管理器初始化完成: {self.tenant_id}")
        except Exception as e:
            self.logger.error(f"产品索引管理器初始化失败: {e}")
            raise
    
    async def index_products(
        self, 
        products_data: List[Dict[str, Any]],
        update_existing: bool = False
    ) -> Dict[str, Any]:
        """
        索引产品数据到RAG系统
        
        Args:
            products_data: 产品数据列表
            update_existing: 是否更新已存在的产品
            
        Returns:
            Dict[str, Any]: 索引结果统计
        """
        if not self.initialized:
            return {
                "success": False,
                "error": "产品索引管理器未初始化",
                "stats": None
            }
        
        if not products_data:
            return {
                "success": False,
                "error": "产品数据为空",
                "stats": None
            }
        
        try:
            self.logger.info(f"开始索引 {len(products_data)} 个产品")
            
            # 执行产品索引
            stats = await self.indexer.index_products_from_data(
                products_data, update_existing
            )
            
            success_rate = (stats.successfully_indexed / stats.total_products) * 100 if stats.total_products > 0 else 0
            
            self.logger.info(
                f"产品索引完成: 成功 {stats.successfully_indexed}/"
                f"{stats.total_products} ({success_rate:.1f}%), "
                f"耗时 {stats.processing_time:.2f}s"
            )
            
            return {
                "success": True,
                "stats": {
                    "total_products": stats.total_products,
                    "successfully_indexed": stats.successfully_indexed,
                    "failed_indexing": stats.failed_indexing,
                    "processing_time": stats.processing_time,
                    "success_rate": success_rate,
                    "errors": stats.errors,
                    "updated_existing": update_existing,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"产品索引失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "stats": None
            }
    
    async def index_single_product(
        self,
        product_data: Dict[str, Any],
        update_existing: bool = False
    ) -> Dict[str, Any]:
        """
        索引单个产品
        
        Args:
            product_data: 单个产品数据
            update_existing: 是否更新已存在的产品
            
        Returns:
            Dict[str, Any]: 索引结果
        """
        try:
            result = await self.index_products([product_data], update_existing)
            
            if result["success"]:
                return {
                    "success": True,
                    "product_id": product_data.get("id", "unknown"),
                    "indexed": result["stats"]["successfully_indexed"] > 0,
                    "processing_time": result["stats"]["processing_time"]
                }
            else:
                return {
                    "success": False,
                    "product_id": product_data.get("id", "unknown"),
                    "error": result["error"]
                }
                
        except Exception as e:
            self.logger.error(f"单个产品索引失败: {e}")
            return {
                "success": False,
                "product_id": product_data.get("id", "unknown"),
                "error": str(e)
            }
    
    async def remove_products(self, product_ids: List[str]) -> Dict[str, Any]:
        """
        从索引中移除产品
        
        Args:
            product_ids: 要移除的产品ID列表
            
        Returns:
            Dict[str, Any]: 移除结果
        """
        if not self.initialized:
            return {
                "success": False,
                "error": "产品索引管理器未初始化"
            }
        
        try:
            removed_count = 0
            errors = []
            
            for product_id in product_ids:
                try:
                    await self.indexer.remove_product(product_id)
                    removed_count += 1
                except Exception as e:
                    errors.append(f"移除产品 {product_id} 失败: {e}")
            
            return {
                "success": True,
                "total_requested": len(product_ids),
                "successfully_removed": removed_count,
                "failed_removals": len(errors),
                "errors": errors
            }
            
        except Exception as e:
            self.logger.error(f"批量移除产品失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_indexing_stats(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        try:
            if not self.initialized:
                return {
                    "initialized": False,
                    "error": "产品索引管理器未初始化"
                }
            
            # 获取索引器统计信息
            indexing_stats = await self.indexer.get_indexing_stats()
            
            return {
                "initialized": True,
                "tenant_id": self.tenant_id,
                "indexing_stats": indexing_stats,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"获取索引统计失败: {e}")
            return {
                "initialized": self.initialized,
                "error": str(e)
            }
    
    async def validate_product_data(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证产品数据格式
        
        Args:
            product_data: 产品数据
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # 必填字段检查
        required_fields = ["id", "name", "category"]
        for field in required_fields:
            if not product_data.get(field):
                validation_result["valid"] = False
                validation_result["errors"].append(f"缺少必填字段: {field}")
        
        # 推荐字段检查
        recommended_fields = ["brand", "price", "description", "benefits"]
        for field in recommended_fields:
            if not product_data.get(field):
                validation_result["warnings"].append(f"建议添加字段: {field}")
        
        # 数据类型检查
        if "price" in product_data:
            try:
                float(product_data["price"])
            except (ValueError, TypeError):
                validation_result["valid"] = False
                validation_result["errors"].append("价格字段必须是数字")
        
        if "rating" in product_data:
            try:
                rating = float(product_data["rating"])
                if not 0 <= rating <= 5:
                    validation_result["warnings"].append("评分应在0-5之间")
            except (ValueError, TypeError):
                validation_result["warnings"].append("评分字段应为数字")
        
        return validation_result
    
    async def bulk_validate_products(self, products_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量验证产品数据
        
        Args:
            products_data: 产品数据列表
            
        Returns:
            Dict[str, Any]: 批量验证结果
        """
        validation_summary = {
            "total_products": len(products_data),
            "valid_products": 0,
            "invalid_products": 0,
            "products_with_warnings": 0,
            "validation_details": []
        }
        
        for i, product_data in enumerate(products_data):
            product_validation = await self.validate_product_data(product_data)
            product_validation["product_index"] = i
            product_validation["product_id"] = product_data.get("id", f"product_{i}")
            
            validation_summary["validation_details"].append(product_validation)
            
            if product_validation["valid"]:
                validation_summary["valid_products"] += 1
            else:
                validation_summary["invalid_products"] += 1
            
            if product_validation["warnings"]:
                validation_summary["products_with_warnings"] += 1
        
        validation_summary["overall_valid"] = validation_summary["invalid_products"] == 0
        validation_summary["validation_rate"] = (
            validation_summary["valid_products"] / validation_summary["total_products"] * 100
            if validation_summary["total_products"] > 0 else 0
        )
        
        return validation_summary
    
    async def get_product_count(self) -> Dict[str, Any]:
        """获取已索引产品数量"""
        try:
            if not self.initialized:
                return {
                    "success": False,
                    "error": "产品索引管理器未初始化"
                }
            
            count = await self.indexer.get_indexed_product_count()
            
            return {
                "success": True,
                "total_products": count,
                "tenant_id": self.tenant_id
            }
            
        except Exception as e:
            self.logger.error(f"获取产品数量失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_manager_info(self) -> Dict[str, Any]:
        """获取管理器基本信息"""
        return {
            "manager_type": "product_indexer",
            "tenant_id": self.tenant_id,
            "initialized": self.initialized,
            "supported_operations": [
                "index_products",
                "index_single_product", 
                "remove_products",
                "validate_product_data",
                "get_indexing_stats"
            ]
        }