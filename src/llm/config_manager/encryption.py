"""
配置加密模块

负责配置数据的加密和解密功能。
"""

import os
import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from src.utils import get_component_logger


class ConfigEncryptionError(Exception):
    """配置加密错误"""
    pass


class ConfigEncryption:
    """配置加密管理器类"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        初始化加密管理器
        
        参数:
            encryption_key: 加密密钥，None时从环境变量获取
        """
        self.logger = get_component_logger(__name__, "ConfigEncryption")
        self.fernet = None
        self._init_encryption(encryption_key)
    
    def _init_encryption(self, encryption_key: Optional[str]):
        """初始化加密功能"""
        try:
            if encryption_key:
                key = encryption_key.encode()
            else:
                # 从环境变量获取或生成密钥
                key_str = os.getenv("LLM_CONFIG_ENCRYPTION_KEY")
                if key_str:
                    key = key_str.encode()
                else:
                    # 生成新密钥
                    key = Fernet.generate_key()
                    self.logger.warning("生成了新的加密密钥，请将其保存到环境变量 LLM_CONFIG_ENCRYPTION_KEY")
                    self.logger.info(f"加密密钥: {key.decode()}")
            
            # 使用PBKDF2派生密钥
            if len(key) < 32:
                salt = b"llm_config_salt"  # 在生产环境中应使用随机盐
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(key))
            
            self.fernet = Fernet(key)
            self.logger.info("配置加密初始化成功")
            
        except Exception as e:
            self.logger.error(f"配置加密初始化失败: {str(e)}")
            self.fernet = None
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """加密敏感数据"""
        if self.fernet is None:
            return data
        
        try:
            encrypted_data = self.fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            raise ConfigEncryptionError(f"数据加密失败: {str(e)}")
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """解密敏感数据"""
        if self.fernet is None:
            return encrypted_data
        
        try:
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.fernet.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            raise ConfigEncryptionError(f"数据解密失败: {str(e)}")
    
    def is_encryption_enabled(self) -> bool:
        """检查是否启用了加密"""
        return self.fernet is not None