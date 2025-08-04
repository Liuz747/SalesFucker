"""
配置验证模块

负责配置数据的验证和完整性检查。
"""

from ..provider_config import ProviderConfig, ProviderType
from .encryption import ConfigEncryption


class ConfigValidationError(Exception):
    """配置验证错误"""
    pass


class ConfigValidator:
    """配置验证器类"""
    
    def __init__(self):
        """初始化配置验证器"""
        pass
    
    async def validate_provider_config(
        self, 
        config: ProviderConfig, 
        encryption: ConfigEncryption
    ) -> bool:
        """
        验证供应商配置
        
        参数:
            config: 供应商配置对象
            encryption: 加密管理器
            
        返回:
            bool: 验证是否通过
            
        异常:
            ConfigValidationError: 验证失败时抛出
        """
        try:
            # 基础验证
            if not config.credentials.api_key:
                raise ConfigValidationError("API密钥不能为空")
            
            if not config.models:
                raise ConfigValidationError("必须配置至少一个模型")
            
            # 供应商特定验证
            if config.provider_type == ProviderType.OPENAI:
                await self._validate_openai_config(config, encryption)
            elif config.provider_type == ProviderType.ANTHROPIC:
                await self._validate_anthropic_config(config, encryption)
            elif config.provider_type == ProviderType.GEMINI:
                await self._validate_gemini_config(config, encryption)
            elif config.provider_type == ProviderType.DEEPSEEK:
                await self._validate_deepseek_config(config, encryption)
            
            return True
            
        except ConfigValidationError:
            raise
        except Exception as e:
            raise ConfigValidationError(f"配置验证失败: {str(e)}")
    
    async def _validate_openai_config(self, config: ProviderConfig, encryption: ConfigEncryption):
        """验证OpenAI配置"""
        api_key = encryption.decrypt_sensitive_data(config.credentials.api_key)
        if not api_key.startswith("sk-"):
            raise ConfigValidationError("OpenAI API密钥格式无效")
    
    async def _validate_anthropic_config(self, config: ProviderConfig, encryption: ConfigEncryption):
        """验证Anthropic配置"""
        api_key = encryption.decrypt_sensitive_data(config.credentials.api_key)
        if not api_key.startswith("sk-ant-"):
            raise ConfigValidationError("Anthropic API密钥格式无效")
    
    async def _validate_gemini_config(self, config: ProviderConfig, encryption: ConfigEncryption):
        """验证Gemini配置"""
        api_key = encryption.decrypt_sensitive_data(config.credentials.api_key)
        if len(api_key) < 10:
            raise ConfigValidationError("Gemini API密钥太短")
    
    async def _validate_deepseek_config(self, config: ProviderConfig, encryption: ConfigEncryption):
        """验证DeepSeek配置"""
        api_key = encryption.decrypt_sensitive_data(config.credentials.api_key)
        if len(api_key) < 10:
            raise ConfigValidationError("DeepSeek API密钥太短")