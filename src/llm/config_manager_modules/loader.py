"""
配置加载器模块

负责配置文件的加载和保存操作。
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from ..provider_config import GlobalProviderConfig, TenantProviderConfig, ProviderConfig, ProviderType
from .encryption import ConfigEncryption
from .serializer import ConfigSerializer


class ConfigLoader:
    """配置加载器类"""
    
    def __init__(self, config_dir: Path, encryption: ConfigEncryption):
        """
        初始化配置加载器
        
        参数:
            config_dir: 配置目录
            encryption: 加密管理器
        """
        self.config_dir = config_dir
        self.encryption = encryption
        self.serializer = ConfigSerializer(encryption)
        
        # 配置文件路径
        self.global_config_file = self.config_dir / "global_config.json"
        self.tenant_configs_dir = self.config_dir / "tenants"
        self.tenant_configs_dir.mkdir(exist_ok=True)
    
    async def load_global_config(self) -> GlobalProviderConfig:
        """加载全局配置"""
        if self.global_config_file.exists():
            config_data = await self._load_config_file(self.global_config_file)
            global_config = self.serializer.parse_global_config(config_data)
        else:
            # 创建默认配置
            global_config = self._create_default_global_config()
            await self.save_global_config(global_config)
        
        # 加载租户配置
        await self._load_tenant_configs(global_config)
        return global_config
    
    async def save_global_config(self, config: GlobalProviderConfig):
        """保存全局配置"""
        config_data = self.serializer.serialize_global_config(config)
        await self._save_config_file(self.global_config_file, config_data)
        
        # 保存租户配置
        await self._save_tenant_configs(config)
    
    async def load_tenant_config(self, tenant_id: str) -> Optional[TenantProviderConfig]:
        """加载租户配置"""
        tenant_config_file = self.tenant_configs_dir / f"{tenant_id}.json"
        
        if tenant_config_file.exists():
            config_data = await self._load_config_file(tenant_config_file)
            tenant_config = self.serializer.parse_tenant_config(config_data)
            return tenant_config
        
        return None
    
    async def save_tenant_config(self, tenant_config: TenantProviderConfig):
        """保存租户配置"""
        tenant_config_file = self.tenant_configs_dir / f"{tenant_config.tenant_id}.json"
        config_data = self.serializer.serialize_tenant_config(tenant_config)
        await self._save_config_file(tenant_config_file, config_data)
    
    def config_file_exists(self, filename: str) -> bool:
        """检查配置文件是否存在"""
        return (self.config_dir / filename).exists()
    
    def get_file_modified_time(self, filename: str) -> datetime:
        """获取文件修改时间"""
        file_path = self.config_dir / filename
        return datetime.fromtimestamp(file_path.stat().st_mtime)
    
    async def _load_config_file(self, file_path: Path) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise ValueError(f"配置文件加载失败 {file_path}: {str(e)}")
    
    async def _save_config_file(self, file_path: Path, config_data: Dict[str, Any]):
        """保存配置文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise ValueError(f"配置文件保存失败 {file_path}: {str(e)}")
    
    def _create_default_global_config(self) -> GlobalProviderConfig:
        """创建默认全局配置"""
        return GlobalProviderConfig(
            default_providers={},
            tenant_configs={},
            global_settings={
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
                "encryption_enabled": self.encryption.is_encryption_enabled()
            }
        )
    
    async def _load_tenant_configs(self, global_config: GlobalProviderConfig):
        """加载所有租户配置"""
        for tenant_file in self.tenant_configs_dir.glob("*.json"):
            tenant_id = tenant_file.stem
            tenant_config = await self.load_tenant_config(tenant_id)
            if tenant_config:
                global_config.tenant_configs[tenant_id] = tenant_config
    
    async def _save_tenant_configs(self, global_config: GlobalProviderConfig):
        """保存所有租户配置"""
        for tenant_id, tenant_config in global_config.tenant_configs.items():
            await self.save_tenant_config(tenant_config)