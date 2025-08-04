"""
备份管理器模块

负责配置的备份和恢复功能。
"""

import json
from typing import Optional
from datetime import datetime
from pathlib import Path

from ..provider_config import GlobalProviderConfig
from .serializer import ConfigSerializer
from .encryption import ConfigEncryption


class BackupManager:
    """备份管理器类"""
    
    def __init__(self, config_dir: Path):
        """
        初始化备份管理器
        
        参数:
            config_dir: 配置目录
        """
        self.config_dir = config_dir
        self.backup_dir = config_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
    
    async def backup_config(
        self, 
        global_config: GlobalProviderConfig,
        serializer: ConfigSerializer,
        backup_dir: Optional[str] = None
    ) -> str:
        """
        备份配置
        
        参数:
            global_config: 全局配置对象
            serializer: 序列化器
            backup_dir: 备份目录，None时使用默认目录
            
        返回:
            str: 备份文件路径
        """
        if backup_dir is None:
            backup_path = self.backup_dir
        else:
            backup_path = Path(backup_dir)
            backup_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_path / f"config_backup_{timestamp}.json"
        
        # 创建完整的备份数据
        backup_data = {
            "backup_timestamp": datetime.now().isoformat(),
            "global_config": serializer.serialize_global_config(global_config),
            "tenant_configs": {}
        }
        
        # 添加租户配置
        for tenant_id, tenant_config in global_config.tenant_configs.items():
            backup_data["tenant_configs"][tenant_id] = serializer.serialize_tenant_config(tenant_config)
        
        # 保存备份文件
        await self._save_backup_file(backup_file, backup_data)
        
        return str(backup_file)
    
    async def restore_config(
        self, 
        backup_file: str,
        serializer: ConfigSerializer
    ) -> GlobalProviderConfig:
        """
        恢复配置
        
        参数:
            backup_file: 备份文件路径
            serializer: 序列化器
            
        返回:
            GlobalProviderConfig: 恢复的全局配置
        """
        backup_path = Path(backup_file)
        if not backup_path.exists():
            raise ValueError(f"备份文件不存在: {backup_file}")
        
        # 加载备份数据
        backup_data = await self._load_backup_file(backup_path)
        
        # 恢复全局配置
        global_config_data = backup_data["global_config"]
        global_config = serializer.parse_global_config(global_config_data)
        
        # 恢复租户配置
        for tenant_id, tenant_data in backup_data.get("tenant_configs", {}).items():
            tenant_config = serializer.parse_tenant_config(tenant_data)
            global_config.tenant_configs[tenant_id] = tenant_config
        
        return global_config
    
    async def _save_backup_file(self, file_path: Path, backup_data: dict):
        """保存备份文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
    
    async def _load_backup_file(self, file_path: Path) -> dict:
        """加载备份文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def list_backups(self) -> list:
        """列出所有备份文件"""
        backup_files = list(self.backup_dir.glob("config_backup_*.json"))
        return [str(f) for f in sorted(backup_files, reverse=True)]
    
    def cleanup_old_backups(self, keep_count: int = 10):
        """清理旧备份文件"""
        backup_files = sorted(self.backup_dir.glob("config_backup_*.json"))
        
        if len(backup_files) > keep_count:
            old_files = backup_files[:-keep_count]
            for old_file in old_files:
                old_file.unlink()