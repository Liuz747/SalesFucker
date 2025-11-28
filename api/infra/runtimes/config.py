"""
LLM配置加载器

从YAML文件加载LLM供应商配置。
"""

from pathlib import Path

from infra.runtimes.entities import Provider, Model, ProviderType, ModelType
from utils.yaml_loader import load_yaml_file
from config import mas_config

class LLMConfig:
    """LLM配置管理器"""

    def __init__(self):
        """初始化配置加载器"""
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "data" / "models.yaml"
        
        self.config_path = str(config_path)
        self.providers = self.load_providers()

    def load_providers(self) -> list[Provider]:
        """
        从YAML文件加载供应商列表
        
        返回:
            list[Provider]: 供应商列表
        """
        yaml_content = load_yaml_file(self.config_path)
        providers = []
        
        api_keys = {
            'openai': mas_config.OPENAI_API_KEY,
            'anthropic': mas_config.ANTHROPIC_API_KEY,
            'gemini': mas_config.GOOGLE_API_KEY,
            'openrouter': mas_config.OPENROUTER_API_KEY,
            'zenmux': mas_config.ZENMUX_API_KEY,
        }
        
        for provider_config in yaml_content:
            provider = provider_config['id']
            
            # 检查是否有对应的API密钥
            api_key = api_keys.get(provider)
            
            if not api_key:
                print(f"No API key found for provider: {provider}")
                continue
        
            # 加载模型列表
            models = []
            for model_config in provider_config['models']:
                if model_config['enabled']:
                    try:
                        model = Model(
                            id=model_config['id'],
                            provider=provider,
                            name=model_config['name'],
                            type=ModelType(model_config['type']),
                            enabled=model_config['enabled']
                        )
                        models.append(model)
                    except KeyError as e:
                        print(f"跳过模型配置 (供应商 {provider}): 缺少字段 {e}")
                        continue
                    except ValueError as e:
                        print(f"跳过模型配置 (供应商 {provider}): 无效值 {e}")
                        continue
            
            try: 
                # 创建供应商实例
                provider = Provider(
                    id=provider,
                    type=ProviderType(provider_config['type']),
                    name=provider_config['name'],
                    api_key=api_key,
                    base_url=provider_config['base_url'],
                    models=models,
                    enabled=provider_config['enabled']
                )
                
                providers.append(provider)
            except KeyError as e:
                print(f"跳过供应商配置: 缺少字段 {e}")
                continue
            except Exception as e:
                print(f"跳过供应商配置: 错误 {e}")
                continue
        
        return providers
