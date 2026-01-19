"""
LLM配置加载器

从YAML文件加载LLM供应商配置。
"""

from pathlib import Path

from config import mas_config
from utils import get_component_logger, load_yaml_file
from .entities import Model, ModelType, Provider, ProviderType

logger = get_component_logger(__name__)


class LLMConfig:
    """LLM配置管理器"""

    def __init__(self):
        """初始化配置加载器"""
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "data" / "models.yaml"

        self.config_path = str(config_path)
        self.providers = self.load_providers()

    @staticmethod
    def _load_models_for_provider(model_configs: list[dict], provider_id: str) -> list[Model]:
        """
        为指定供应商加载模型列表

        参数:
            model_configs: 模型配置列表
            provider_id: 供应商ID

        返回:
            list[Model]: 模型列表
        """
        models = []
        for model_config in model_configs:
            if not model_config.get('enabled', False):
                continue

            try:
                model = Model(
                    id=model_config['id'],
                    provider=provider_id,
                    name=model_config['name'],
                    type=ModelType(model_config['type'])
                )
                models.append(model)
            except KeyError as e:
                logger.warning(f"跳过模型配置 (供应商 {provider_id}): 缺少字段 {e}")
                continue
            except ValueError as e:
                logger.warning(f"跳过模型配置 (供应商 {provider_id}): 无效值 {e}")
                continue

        return models

    def load_providers(self) -> list[Provider]:
        """
        从YAML文件加载供应商列表

        返回:
            list[Provider]: 供应商列表
        """
        yaml_content: list[dict] = load_yaml_file(self.config_path)
        providers = []

        api_keys = {
            'anthropic': mas_config.ANTHROPIC_API_KEY,
            'dashscope': mas_config.DASHSCOPE_API_KEY,
            'gemini': mas_config.GOOGLE_API_KEY,
            'openai': mas_config.OPENAI_API_KEY,
            'openrouter': mas_config.OPENROUTER_API_KEY,
            # 'zenmux': mas_config.ZENMUX_API_KEY,
        }

        for provider_config in yaml_content:
            provider_id = provider_config['id']

            # 检查供应商是否启用
            if not provider_config.get('enabled', False):
                logger.info(f"跳过未启用的供应商: {provider_id}")
                continue

            # 检查是否有对应的API密钥
            api_key = api_keys.get(provider_id)
            if not api_key:
                logger.warning(f"No API key found for provider: {provider_id}")
                continue

            # 加载模型列表
            models = self._load_models_for_provider(provider_config['models'], provider_id)

            try:
                # 创建供应商实例
                provider = Provider(
                    id=provider_id,
                    type=ProviderType(provider_config['type']),
                    name=provider_config['name'],
                    api_key=api_key,
                    base_url=provider_config['base_url'],
                    models=models
                )
                providers.append(provider)
            except KeyError as e:
                logger.error(f"跳过供应商配置: 缺少字段 {e}")
                continue
            except Exception as e:
                logger.error(f"跳过供应商配置: 错误 {e}")
                continue

        return providers
