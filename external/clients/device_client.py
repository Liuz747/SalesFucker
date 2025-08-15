"""
设备查询客户端

该模块提供设备信息查询功能，通过调用后端API获取设备数据。
不包含设备管理功能，只负责查询操作。

主要功能:
- 设备信息查询
- 设备验证
- 设备能力查询
- 设备在线状态检查
"""

from typing import Dict, Any, Optional, List

from ..base_client import BaseClient, ExternalAPIError
from ..config import get_external_config
from src.utils import get_component_logger


class DeviceClient(BaseClient):
    """
    设备查询客户端
    
    负责与后端API通信，查询设备相关信息。
    """
    
    def __init__(self, config: Optional[Any] = None):
        """
        初始化设备客户端
        
        参数:
            config: 外部API配置，如果为None则使用全局配置
        """
        if config is None:
            config = get_external_config()
        
        super().__init__(
            base_url=config.backend_api_base_url,
            timeout=config.backend_api_timeout,
            max_retries=config.backend_api_max_retries
        )
        
        self.config = config
        self.logger = get_component_logger(__name__, "DeviceClient")
        
        self.logger.info(f"设备客户端初始化完成: {config.backend_api_base_url}")
    
    def _get_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """获取请求头，包含认证信息"""
        headers = self.config.backend_headers
        
        if additional_headers:
            headers.update(additional_headers)
        
        return headers
    
    async def get_device(self, device_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        获取设备详细信息
        
        参数:
            device_id: 设备ID
            tenant_id: 租户ID
            
        返回:
            设备信息字典，如果设备不存在返回None
        """
        try:
            self.logger.debug(f"查询设备信息: device_id={device_id}, tenant_id={tenant_id}")
            
            response = await self.get(
                f"devices/{device_id}",
                params={"tenant_id": tenant_id},
                headers=self._get_headers()
            )
            
            # 检查响应格式
            if "data" in response:
                device_info = response["data"]
            else:
                device_info = response
            
            self.logger.debug(f"设备信息获取成功: {device_id}")
            return device_info
            
        except ExternalAPIError as e:
            if e.status_code == 404:
                self.logger.warning(f"设备不存在: {device_id}")
                return None
            else:
                self.logger.error(f"获取设备信息失败: {e}")
                raise
    
    async def validate_device(self, device_id: str, tenant_id: str) -> bool:
        """
        验证设备是否存在
        
        参数:
            device_id: 设备ID
            tenant_id: 租户ID
            
        返回:
            设备是否存在
        """
        try:
            device_info = await self.get_device(device_id, tenant_id)
            return device_info is not None
            
        except Exception as e:
            self.logger.error(f"设备验证失败: device_id={device_id}, error={e}")
            return False
    
    async def get_device_capabilities(self, device_id: str, tenant_id: str) -> List[str]:
        """
        获取设备能力列表
        
        参数:
            device_id: 设备ID
            tenant_id: 租户ID
            
        返回:
            设备能力列表（如：['camera', 'microphone', 'speaker']）
        """
        try:
            self.logger.debug(f"查询设备能力: device_id={device_id}")
            
            response = await self.get(
                f"devices/{device_id}/capabilities",
                params={"tenant_id": tenant_id},
                headers=self._get_headers()
            )
            
            capabilities = response.get("capabilities", [])
            
            self.logger.debug(f"设备能力获取成功: {device_id}, capabilities={capabilities}")
            return capabilities
            
        except ExternalAPIError as e:
            if e.status_code == 404:
                self.logger.warning(f"设备不存在: {device_id}")
                return []
            else:
                self.logger.error(f"获取设备能力失败: {e}")
                return []  # 返回空列表而不是抛出异常
    
    async def check_device_online(self, device_id: str, tenant_id: str) -> bool:
        """
        检查设备在线状态
        
        参数:
            device_id: 设备ID
            tenant_id: 租户ID
            
        返回:
            设备是否在线
        """
        try:
            self.logger.debug(f"检查设备在线状态: device_id={device_id}")
            
            response = await self.get(
                f"devices/{device_id}/status",
                params={"tenant_id": tenant_id},
                headers=self._get_headers()
            )
            
            is_online = response.get("is_online", False)
            
            self.logger.debug(f"设备在线状态: {device_id}, online={is_online}")
            return is_online
            
        except Exception as e:
            self.logger.error(f"检查设备在线状态失败: device_id={device_id}, error={e}")
            return False  # 出错时假设设备离线
    
    async def get_device_info_for_conversation(self, device_id: str, tenant_id: str) -> Dict[str, Any]:
        """
        获取对话所需的设备信息
        
        参数:
            device_id: 设备ID
            tenant_id: 租户ID
            
        返回:
            对话相关的设备信息
        """
        try:
            self.logger.debug(f"获取对话设备信息: device_id={device_id}")
            
            # 并发获取设备信息和能力
            device_info_task = self.get_device(device_id, tenant_id)
            capabilities_task = self.get_device_capabilities(device_id, tenant_id)
            online_status_task = self.check_device_online(device_id, tenant_id)
            
            device_info, capabilities, is_online = await asyncio.gather(
                device_info_task,
                capabilities_task, 
                online_status_task,
                return_exceptions=True
            )
            
            # 处理异常结果
            if isinstance(device_info, Exception):
                device_info = None
            if isinstance(capabilities, Exception):
                capabilities = []
            if isinstance(is_online, Exception):
                is_online = False
            
            # 如果设备不存在，返回基本信息
            if device_info is None:
                return {
                    "device_id": device_id,
                    "exists": False,
                    "capabilities": [],
                    "is_online": False
                }
            
            # 构建对话所需的设备信息
            conversation_device_info = {
                "device_id": device_id,
                "exists": True,
                "device_name": device_info.get("device_name", ""),
                "device_type": device_info.get("device_type", ""),
                "platform": device_info.get("platform", ""),
                "capabilities": capabilities,
                "is_online": is_online,
                "supports_voice": "microphone" in capabilities and "speaker" in capabilities,
                "supports_camera": "camera" in capabilities,
                "supports_multimodal": len(capabilities) > 1
            }
            
            self.logger.debug(f"对话设备信息获取成功: {device_id}")
            return conversation_device_info
            
        except Exception as e:
            self.logger.error(f"获取对话设备信息失败: device_id={device_id}, error={e}")
            
            # 返回基本的错误状态
            return {
                "device_id": device_id,
                "exists": False,
                "capabilities": [],
                "is_online": False,
                "error": str(e)
            }
    
    async def batch_validate_devices(self, device_ids: List[str], tenant_id: str) -> Dict[str, bool]:
        """
        批量验证设备
        
        参数:
            device_ids: 设备ID列表
            tenant_id: 租户ID
            
        返回:
            设备ID到存在状态的映射
        """
        try:
            self.logger.debug(f"批量验证设备: device_ids={device_ids}")
            
            response = await self.post(
                "devices/batch-validate",
                data={
                    "device_ids": device_ids,
                    "tenant_id": tenant_id
                },
                headers=self._get_headers()
            )
            
            validation_results = response.get("results", {})
            
            self.logger.debug(f"批量设备验证完成: {len(validation_results)}个结果")
            return validation_results
            
        except Exception as e:
            self.logger.error(f"批量设备验证失败: {e}")
            
            # 回退到单个验证
            results = {}
            for device_id in device_ids:
                try:
                    results[device_id] = await self.validate_device(device_id, tenant_id)
                except:
                    results[device_id] = False
            
            return results


# 导入asyncio
import asyncio


# 全局客户端实例
_device_client: Optional[DeviceClient] = None


def get_device_client() -> DeviceClient:
    """获取全局设备客户端实例"""
    global _device_client
    
    if _device_client is None:
        _device_client = DeviceClient()
    
    return _device_client


async def close_device_client():
    """关闭全局设备客户端"""
    global _device_client
    
    if _device_client:
        await _device_client.close()
        _device_client = None