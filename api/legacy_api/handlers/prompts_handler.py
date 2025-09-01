"""
提示词处理器

该模块提供提示词管理的业务逻辑处理，包括提示词配置、验证、测试
和库管理等功能。支持基于提示词的智能体个性化定制。

主要功能:
- 提示词配置管理
- 提示词测试和验证
- 提示词库管理
- 版本控制和历史记录
"""

import uuid
import re
from typing import Optional, Dict, Any, List
from datetime import datetime

from models.prompts import PromptsModel, PromptsOrmModel
from services.prompts_dao import PromptsDao
from ..schemas.prompts import (
    PromptCreateRequest, PromptUpdateRequest, PromptTestRequest,
    PromptLibrarySearchRequest, PromptConfigResponse, PromptTestResponse,
    PromptLibraryResponse, PromptValidationResponse,
    AssistantPromptConfig, PromptLibraryItem,
    PromptCategory, PromptType, PromptLanguage
)
from utils import get_component_logger, with_error_handling, StatusMixin


class PromptHandler(StatusMixin):
    """
    提示词处理器
    
    处理智能体提示词相关的业务逻辑，包括配置管理、测试验证和库管理。
    """

    def __init__(self):
        """初始化提示词处理器"""
        super().__init__()
        self.logger = get_component_logger(__name__)

        # 模拟数据存储（实际应用中应该使用数据库）
        self._prompt_configs: Dict[str, Dict[str, Any]] = {}
        self._prompt_history: Dict[str, List[Dict[str, Any]]] = {}
        self._prompt_library: List[PromptLibraryItem] = []

        # 初始化提示词库
        self._initialize_prompt_library()

        self.logger.info("提示词处理器初始化完成")

    @with_error_handling(fallback_response=None)
    async def create_assistant_prompts(self, request: PromptCreateRequest) -> PromptsModel:
        """
        创建助理提示词配置
        
        参数:
            request: 提示词创建请求
            
        返回:
            PromptConfigResponse: 配置结果
        """
        try:
            config_key = f"{request.tenant_id}:{request.assistant_id}"

            # 验证提示词配置
            await self._validate_prompt_config(request.prompt_config)

            now = datetime.utcnow()
            config_data = {
                "assistant_id": request.assistant_id,
                "tenant_id": request.tenant_id,
                "config": request.prompt_config.dict(),
                "created_at": now,
                "updated_at": now,
                "version": request.prompt_config.version,
                "is_active": request.prompt_config.is_active
            }

            prompts_model = PromptsModel(
                tenant_id=request.assistant_id,
                assistant_id=request.assistant_id,
                personality_prompt=request.prompt_config.personality_prompt,
                greeting_prompt=request.prompt_config.greeting_prompt,
                product_recommendation_prompt=request.prompt_config.product_recommendation_prompt,
                objection_handling_prompt=request.prompt_config.tenant_id,
                closing_prompt=request.prompt_config.closing_prompt,
                context_instructions=request.prompt_config.context_instructions,
                llm_parameters=request.prompt_config.llm_parameters,
                safety_guidelines=request.prompt_config.safety_guidelines,
                forbidden_topics=request.prompt_config.forbidden_topics,
                brand_voice=request.prompt_config.brand_voice,
                product_knowledge=request.prompt_config.product_knowledge,
                version=request.prompt_config.version,
                is_active=request.prompt_config.is_active,
                created_at=now,
                updated_at=now
            )

            id = await PromptsDao.insertPrompts(prompts_model.to_orm())
            prompts_model.id = id
            # todo 记录历史版本 功能存疑，需要确认
            # if config_key not in self._prompt_history:
            #     self._prompt_history[config_key] = []
            # self._prompt_history[config_key].append(config_data.copy())

            self.logger.error(f"助理提示词配置创建成功: {request.assistant_id} {prompts_model}")

            return prompts_model

        except Exception as e:
            self.logger.error(f"助理提示词配置创建失败: {e}")
            raise

    @with_error_handling(fallback_response=None)
    async def get_assistant_prompts(
            self,
            assistant_id: str,
            tenant_id: str,
            version: Optional[str] = None
    ) -> Optional[PromptsModel]:
        """
        获取助理提示词配置
        
        参数:
            assistant_id: 助理ID
            tenant_id: 租户ID
            version: 指定版本（可选）
            
        返回:
            Optional[PromptConfigResponse]: 配置信息
        """
        try:
            # config_key = f"{tenant_id}:{assistant_id}"

            # 不确定版本的定义，先不考虑
            if 1 == 2:
                if version:
                    # 获取指定版本
                    history = self._prompt_history.get(config_key, [])
                    for config in history:
                        if config.get("version") == version:
                            prompt_config = AssistantPromptConfig(**config["config"])
                            return PromptConfigResponse(
                                success=True,
                                message="历史版本提示词配置查询成功",
                                data={},
                                assistant_id=assistant_id,
                                tenant_id=tenant_id,
                                config=prompt_config,
                                created_at=config["created_at"],
                                updated_at=config["updated_at"]
                            )
                    return None

            # 获取当前版本
            prompts_orm = await PromptsDao.get_prompts(assistant_id, tenant_id, version)
            if not prompts_orm:
                return None

            self.logger.info(f"助理提示词配置查询成功: {assistant_id}")

            return prompts_orm.to_model()

        except Exception as e:
            self.logger.error(f"助理提示词配置查询失败: {e}")
            raise

    @with_error_handling(fallback_response=None)
    async def update_assistant_prompts(
            self,
            assistant_id: str,
            tenant_id: str,
            request: PromptUpdateRequest
    ) -> Optional[PromptConfigResponse]:
        """
        更新助理提示词配置
        
        参数:
            assistant_id: 助理ID
            tenant_id: 租户ID
            request: 更新请求
            
        返回:
            Optional[PromptConfigResponse]: 更新后的配置
        """
        try:
            config_key = f"{tenant_id}:{assistant_id}"
            config_data = self._prompt_configs.get(config_key)

            if not config_data:
                return None

            # 创建新版本
            current_config = AssistantPromptConfig(**config_data["config"])

            # 应用更新
            update_fields = {}
            if request.personality_prompt is not None:
                update_fields["personality_prompt"] = request.personality_prompt
            if request.greeting_prompt is not None:
                update_fields["greeting_prompt"] = request.greeting_prompt
            if request.product_recommendation_prompt is not None:
                update_fields["product_recommendation_prompt"] = request.product_recommendation_prompt
            if request.objection_handling_prompt is not None:
                update_fields["objection_handling_prompt"] = request.objection_handling_prompt
            if request.closing_prompt is not None:
                update_fields["closing_prompt"] = request.closing_prompt
            if request.context_instructions is not None:
                update_fields["context_instructions"] = request.context_instructions
            if request.llm_parameters is not None:
                current_params = current_config.llm_parameters or {}
                update_fields["llm_parameters"] = {**current_params, **request.llm_parameters}
            if request.brand_voice is not None:
                update_fields["brand_voice"] = request.brand_voice
            if request.product_knowledge is not None:
                update_fields["product_knowledge"] = request.product_knowledge
            if request.safety_guidelines is not None:
                update_fields["safety_guidelines"] = request.safety_guidelines
            if request.forbidden_topics is not None:
                update_fields["forbidden_topics"] = request.forbidden_topics
            if request.is_active is not None:
                update_fields["is_active"] = request.is_active

            # 更新版本号
            current_version = current_config.version.split('.')
            current_version[-1] = str(int(current_version[-1]) + 1)
            update_fields["version"] = '.'.join(current_version)

            # 创建更新后的配置
            updated_config_dict = current_config.dict()
            updated_config_dict.update(update_fields)
            updated_config = AssistantPromptConfig(**updated_config_dict)

            # 验证更新后的配置
            await self._validate_prompt_config(updated_config)

            now = datetime.utcnow()
            new_config_data = {
                "assistant_id": assistant_id,
                "tenant_id": tenant_id,
                "config": updated_config.dict(),
                "created_at": config_data["created_at"],
                "updated_at": now,
                "version": updated_config.version,
                "is_active": updated_config.is_active
            }

            # 保存到历史记录
            self._prompt_history[config_key].append(config_data.copy())

            # 更新当前配置
            self._prompt_configs[config_key] = new_config_data

            self.logger.info(f"助理提示词配置更新成功: {assistant_id}, 版本: {updated_config.version}")

            return PromptConfigResponse(
                success=True,
                message="提示词配置更新成功",
                data={},
                assistant_id=assistant_id,
                tenant_id=tenant_id,
                config=updated_config,
                created_at=new_config_data["created_at"],
                updated_at=new_config_data["updated_at"]
            )

        except Exception as e:
            self.logger.error(f"助理提示词配置更新失败: {e}")
            raise

    @with_error_handling(fallback_response=None)
    async def test_assistant_prompts(
            self,
            assistant_id: str,
            tenant_id: str,
            request: PromptTestRequest
    ) -> PromptTestResponse:
        """
        测试助理提示词效果
        
        参数:
            assistant_id: 助理ID
            tenant_id: 租户ID
            request: 测试请求
            
        返回:
            PromptTestResponse: 测试结果
        """
        try:
            test_id = str(uuid.uuid4())

            # 模拟测试过程
            test_results = []
            total_score = 0

            for i, scenario in enumerate(request.test_scenarios):
                # 模拟LLM调用和响应生成
                test_result = await self._simulate_prompt_test(
                    request.prompt_config, scenario, request.llm_provider, request.model_name
                )
                test_results.append({
                    "scenario_id": i + 1,
                    "input": scenario["input"],
                    "context": scenario.get("context", {}),
                    "generated_response": test_result["response"],
                    "score": test_result["score"],
                    "metrics": test_result["metrics"],
                    "issues": test_result["issues"]
                })
                total_score += test_result["score"]

            overall_score = total_score / len(request.test_scenarios) if request.test_scenarios else 0

            # 生成优化建议
            recommendations = await self._generate_recommendations(test_results, request.prompt_config)

            # 计算性能指标
            performance_metrics = {
                "average_response_length": sum(len(r["generated_response"]) for r in test_results) / len(test_results),
                "consistency_score": self._calculate_consistency_score(test_results),
                "safety_score": self._calculate_safety_score(test_results),
                "relevance_score": self._calculate_relevance_score(test_results)
            }

            self.logger.info(f"助理提示词测试完成: {assistant_id}, 总体评分: {overall_score:.2f}")

            return PromptTestResponse(
                success=True,
                message="提示词测试完成",
                data={},
                test_id=test_id,
                test_results=test_results,
                overall_score=overall_score,
                recommendations=recommendations,
                performance_metrics=performance_metrics
            )

        except Exception as e:
            self.logger.error(f"助理提示词测试失败: {e}")
            raise

    @with_error_handling(fallback_response=None)
    async def validate_assistant_prompts(
            self,
            assistant_id: str,
            tenant_id: str,
            prompt_config: AssistantPromptConfig
    ) -> PromptValidationResponse:
        """
        验证助理提示词配置
        
        参数:
            assistant_id: 助理ID
            tenant_id: 租户ID
            prompt_config: 提示词配置
            
        返回:
            PromptValidationResponse: 验证结果
        """
        try:
            validation_results = {}
            suggestions = []
            is_valid = True

            # 1. 基础格式验证
            format_validation = await self._validate_prompt_format(prompt_config)
            validation_results["format"] = format_validation
            if not format_validation["valid"]:
                is_valid = False
                suggestions.extend(format_validation["suggestions"])

            # 2. 安全性验证
            safety_validation = await self._validate_prompt_safety(prompt_config)
            validation_results["safety"] = safety_validation
            if not safety_validation["valid"]:
                is_valid = False
                suggestions.extend(safety_validation["suggestions"])

            # 3. 合规性验证
            compliance_validation = await self._validate_prompt_compliance(prompt_config)
            validation_results["compliance"] = compliance_validation
            if not compliance_validation["valid"]:
                is_valid = False
                suggestions.extend(compliance_validation["suggestions"])

            # 4. 效果预估
            performance_validation = await self._validate_prompt_performance(prompt_config)
            validation_results["performance"] = performance_validation
            suggestions.extend(performance_validation["suggestions"])

            # 计算预估性能指标
            estimated_performance = {
                "clarity_score": performance_validation.get("clarity_score", 0.8),
                "consistency_score": performance_validation.get("consistency_score", 0.7),
                "effectiveness_score": performance_validation.get("effectiveness_score", 0.75)
            }

            self.logger.info(f"助理提示词验证完成: {assistant_id}, 有效性: {is_valid}")

            return PromptValidationResponse(
                success=True,
                message="提示词验证完成",
                data={},
                is_valid=is_valid,
                validation_results=validation_results,
                suggestions=suggestions,
                estimated_performance=estimated_performance
            )

        except Exception as e:
            self.logger.error(f"助理提示词验证失败: {e}")
            raise

    @with_error_handling(fallback_response=None)
    async def get_prompt_library(self, request: PromptLibrarySearchRequest) -> PromptLibraryResponse:
        """
        获取提示词库
        
        参数:
            request: 搜索请求
            
        返回:
            PromptLibraryResponse: 提示词库内容
        """
        try:
            # 筛选提示词库
            filtered_items = []

            for item in self._prompt_library:
                # 分类筛选
                if request.category and item.category != request.category:
                    continue

                # 类型筛选
                if request.prompt_type and item.prompt_type != request.prompt_type:
                    continue

                # 语言筛选
                if request.language and item.language != request.language:
                    continue

                # 关键词搜索
                if request.search_text:
                    search_text = request.search_text.lower()
                    if not (search_text in item.title.lower() or
                            search_text in item.use_case.lower() or
                            search_text in item.prompt_content.lower()):
                        continue

                filtered_items.append(item)

            # 排序
            reverse = request.sort_order == "desc"
            if request.sort_by == "rating":
                filtered_items.sort(key=lambda x: x.rating, reverse=reverse)
            elif request.sort_by == "usage_count":
                filtered_items.sort(key=lambda x: x.usage_count, reverse=reverse)
            elif request.sort_by == "created_at":
                filtered_items.sort(key=lambda x: x.created_at, reverse=reverse)

            # 分页
            total_count = len(filtered_items)
            start_idx = (request.page - 1) * request.page_size
            end_idx = start_idx + request.page_size
            paginated_items = filtered_items[start_idx:end_idx]

            # 统计信息
            categories = {}
            languages = {}

            for item in self._prompt_library:
                categories[item.category.value] = categories.get(item.category.value, 0) + 1
                languages[item.language.value] = languages.get(item.language.value, 0) + 1

            self.logger.info(f"提示词库查询成功: 返回{len(paginated_items)}/{total_count}条记录")

            return PromptLibraryResponse(
                success=True,
                message="提示词库查询成功",
                data=paginated_items,
                items=paginated_items,
                categories=categories,
                languages=languages,
                total=total_count,
                page=request.page,
                page_size=request.page_size,
                pages=(total_count + request.page_size - 1)  # request.page_size,
            )

        except Exception as e:
            self.logger.error(f"提示词库查询失败: {e}")
            raise

    async def clone_assistant_prompts(
            self,
            source_assistant_id: str,
            target_assistant_id: str,
            tenant_id: str,
            modify_personality: bool = False
    ) -> PromptsModel:
        """克隆助理提示词配置"""
        try:
            # source_key = f"{tenant_id}:{source_assistant_id}"
            # source_config = self._prompt_configs.get(source_key)

            # 获取当前版本
            # todo 需要指定 version
            source_config = await PromptsDao.get_prompts(source_assistant_id, tenant_id, "")
            if not source_config:
                return None

            # 复制配置
            cloned_config_dict = PromptsOrmModel(
                id=None,
                tenant_id=source_config.tenant_id,
                assistant_id=source_config.assistant_id,
                personality_prompt=source_config.personality_prompt,
                greeting_prompt=source_config.greeting_prompt,
                product_recommendation_prompt=source_config.product_recommendation_prompt,
                objection_handling_prompt=source_config.tenant_id,
                closing_prompt=source_config.closing_prompt,
                context_instructions=source_config.context_instructions,
                llm_parameters=source_config.llm_parameters,
                safety_guidelines=source_config.safety_guidelines,
                forbidden_topics=source_config.forbidden_topics,
                brand_voice=source_config.brand_voice,
                product_knowledge=source_config.product_knowledge,
                version=source_config.version,
                is_active=source_config.is_active,
                created_at=source_config.created_at,
                updated_at=source_config.updated_at
            )
            cloned_config_dict.assistant_id = target_assistant_id

            if modify_personality:
                # 修改个性化部分，避免完全相同
                cloned_config_dict.personality_prompt = f"{cloned_config_dict.personality_prompt}\n\n注意：作为{target_assistant_id}，请保持独特的个性特色。"

            # 更新版本
            cloned_config_dict.version = "1.0.0"

            # 创建克隆请求
            # create_request = PromptCreateRequest(
            #     assistant_id=target_assistant_id,
            #     tenant_id=tenant_id,
            #     prompt_config=cloned_config
            # )
            #
            # return await self.create_assistant_prompts(create_request)
            r = await PromptsDao.insertPrompts(cloned_config_dict)
            cloned_config_dict.id = r
            return cloned_config_dict.to_model()

        except Exception as e:
            self.logger.error(f"助理提示词克隆失败: {e}")
            raise

    async def get_prompt_history(
            self,
            assistant_id: str,
            tenant_id: str,
            limit: int = 10
    ) -> list[PromptsModel]:
        """获取提示词历史版本"""
        try:
            config_key = f"{tenant_id}:{assistant_id}"
            # history = self._prompt_history.get(config_key, [])

            # 按时间倒序排序
            # history.sort(key=lambda x: x["updated_at"], reverse=True)

            # 限制数量
            # limited_history = history[:limit]

            # responses = []
            # for config_data in limited_history:
            #     prompt_config = AssistantPromptConfig(**config_data["config"])
            #     responses.append(PromptConfigResponse(
            #         success=True,
            #         message="历史版本",
            #         data={},
            #         assistant_id=assistant_id,
            #         tenant_id=tenant_id,
            #         config=prompt_config,
            #         created_at=config_data["created_at"],
            #         updated_at=config_data["updated_at"]
            #     ))

            r = await PromptsDao.get_prompts_list_order(tenant_id, assistant_id, limit)
            l: list[PromptsModel] = []
            for prompt in r:
                l.append(prompt.to_model())

            return l

        except Exception as e:
            self.logger.error(f"提示词历史查询失败: {e}")
            raise

    async def rollback_assistant_prompts(
            self,
            assistant_id: str,
            tenant_id: str,
            version: str
    ) -> Optional[PromptsModel]:
        """回退提示词配置到指定版本"""
        try:
            config_key = f"{tenant_id}:{assistant_id}"
            # history = self._prompt_history.get(config_key, [])

            target_config = await PromptsDao.get_prompts(tenant_id, assistant_id, version)
            if not target_config:
                return None

            # 创建新版本（基于历史版本）
            rollback_config = PromptsOrmModel(
                id=None,
                tenant_id=target_config.tenant_id,
                assistant_id=target_config.assistant_id,
                personality_prompt=target_config.personality_prompt,
                greeting_prompt=target_config.greeting_prompt,
                product_recommendation_prompt=target_config.product_recommendation_prompt,
                objection_handling_prompt=target_config.tenant_id,
                closing_prompt=target_config.closing_prompt,
                context_instructions=target_config.context_instructions,
                llm_parameters=target_config.llm_parameters,
                safety_guidelines=target_config.safety_guidelines,
                forbidden_topics=target_config.forbidden_topics,
                brand_voice=target_config.brand_voice,
                product_knowledge=target_config.product_knowledge,
                version=target_config.version,
                is_active=target_config.is_active,
                created_at=target_config.created_at,
                updated_at=target_config.updated_at
            )

            # 更新版本号
            current_version = rollback_config.version.split('.')
            current_version[0] = str(int(current_version[0]) + 1)
            rollback_config.version = '.'.join(current_version)
            rollback_config.updated_at = datetime.utcnow()

            id = await PromptsDao.insertPrompts(rollback_config)
            rollback_config.id=id
            self.logger.info(f"提示词配置回退成功: {assistant_id}, 回退到版本: {version}")
            return rollback_config.to_model()
        except Exception as e:
            self.logger.error(f"提示词配置回退失败: {e}")
            raise

    # 私有辅助方法

    async def _validate_prompt_config(self, config: AssistantPromptConfig) -> None:
        """验证提示词配置的基本有效性"""
        if not config.personality_prompt or len(config.personality_prompt.strip()) < 50:
            raise ValueError("个性化提示词长度不能少于50个字符")

        if len(config.personality_prompt) > 4000:
            raise ValueError("个性化提示词长度不能超过4000个字符")

        # 检查危险关键词
        dangerous_keywords = ["ignore", "forget", "system", "override", "jailbreak"]
        for keyword in dangerous_keywords:
            if keyword in config.personality_prompt.lower():
                raise ValueError(f"提示词包含危险关键词: {keyword}")

    async def _simulate_prompt_test(
            self,
            config: AssistantPromptConfig,
            scenario: Dict[str, Any],
            llm_provider: Optional[str] = None,
            model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """模拟提示词测试"""
        # 模拟LLM响应生成
        response_templates = [
            "您好！很高兴为您服务。根据您的需求，我推荐...",
            "感谢您的咨询！基于我的专业知识，我建议...",
            "了解了您的情况，我认为最适合您的是...",
        ]

        import random
        simulated_response = random.choice(response_templates) + scenario["input"][:50] + "的专业建议。"

        # 模拟评分
        score = random.uniform(0.7, 0.95)

        # 模拟指标
        metrics = {
            "response_time": random.uniform(0.5, 2.0),
            "token_count": len(simulated_response.split()),
            "safety_score": random.uniform(0.8, 1.0),
            "relevance_score": random.uniform(0.7, 0.9)
        }

        # 模拟问题检测
        issues = []
        if score < 0.8:
            issues.append("响应相关性需要提升")
        if len(simulated_response) < 50:
            issues.append("响应过于简短")

        return {
            "response": simulated_response,
            "score": score,
            "metrics": metrics,
            "issues": issues
        }

    async def _generate_recommendations(
            self,
            test_results: List[Dict[str, Any]],
            config: AssistantPromptConfig
    ) -> List[str]:
        """生成优化建议"""
        recommendations = []

        avg_score = sum(r["score"] for r in test_results) / len(test_results)

        if avg_score < 0.8:
            recommendations.append("建议优化个性化提示词，提高响应质量")

        avg_length = sum(len(r["generated_response"]) for r in test_results) / len(test_results)
        if avg_length < 100:
            recommendations.append("响应长度偏短，建议增加更详细的说明")
        elif avg_length > 500:
            recommendations.append("响应长度偏长，建议简化表达")

        # 检查安全性
        safety_issues = sum(1 for r in test_results if "safety" in str(r.get("issues", [])))
        if safety_issues > 0:
            recommendations.append("检测到安全性问题，建议加强安全指导原则")

        if not recommendations:
            recommendations.append("提示词配置良好，可以考虑进行A/B测试进一步优化")

        return recommendations

    def _calculate_consistency_score(self, test_results: List[Dict[str, Any]]) -> float:
        """计算一致性评分"""
        scores = [r["score"] for r in test_results]
        if not scores:
            return 0.0

        # 计算标准差，标准差越小一致性越高
        import statistics
        std_dev = statistics.stdev(scores) if len(scores) > 1 else 0
        consistency_score = max(0, 1 - std_dev)
        return round(consistency_score, 2)

    def _calculate_safety_score(self, test_results: List[Dict[str, Any]]) -> float:
        """计算安全性评分"""
        total_safety = sum(r["metrics"].get("safety_score", 0.8) for r in test_results)
        return round(total_safety / len(test_results), 2) if test_results else 0.8

    def _calculate_relevance_score(self, test_results: List[Dict[str, Any]]) -> float:
        """计算相关性评分"""
        total_relevance = sum(r["metrics"].get("relevance_score", 0.7) for r in test_results)
        return round(total_relevance / len(test_results), 2) if test_results else 0.7

    async def _validate_prompt_format(self, config: AssistantPromptConfig) -> Dict[str, Any]:
        """验证提示词格式"""
        issues = []

        if not config.personality_prompt.strip():
            issues.append("个性化提示词不能为空")

        if len(config.personality_prompt) < 50:
            issues.append("个性化提示词过短，建议至少50个字符")

        # 检查是否包含基本要素
        required_elements = ["身份", "角色", "目标"]
        for element in required_elements:
            if element not in config.personality_prompt:
                issues.append(f"建议在提示词中明确{element}定义")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "suggestions": issues
        }

    async def _validate_prompt_safety(self, config: AssistantPromptConfig) -> Dict[str, Any]:
        """验证提示词安全性"""
        issues = []

        # 检查禁止词汇
        dangerous_patterns = [
            r"ignore.*instructions?",
            r"forget.*context",
            r"system.*override",
            r"jailbreak",
            r"bypass.*safety"
        ]

        text_to_check = config.personality_prompt.lower()
        for pattern in dangerous_patterns:
            if re.search(pattern, text_to_check):
                issues.append(f"检测到潜在安全风险模式: {pattern}")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "suggestions": [f"建议移除或修改: {issue}" for issue in issues]
        }

    async def _validate_prompt_compliance(self, config: AssistantPromptConfig) -> Dict[str, Any]:
        """验证提示词合规性"""
        issues = []
        suggestions = []

        # 检查是否包含合规指导
        if not config.safety_guidelines:
            issues.append("缺少安全指导原则")
            suggestions.append("建议添加安全指导原则")

        if not config.forbidden_topics:
            suggestions.append("建议添加禁止讨论的话题列表")

        # 检查品牌合规性
        if not config.brand_voice:
            suggestions.append("建议添加品牌声音定义")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "suggestions": suggestions
        }

    async def _validate_prompt_performance(self, config: AssistantPromptConfig) -> Dict[str, Any]:
        """验证提示词性能预估"""
        suggestions = []

        # 分析提示词结构
        clarity_score = 0.8  # 模拟评分
        if len(config.personality_prompt.split('.')) < 3:
            suggestions.append("建议增加更多具体的行为指导")
            clarity_score -= 0.1

        consistency_score = 0.7
        if config.greeting_prompt and config.closing_prompt:
            consistency_score += 0.1

        effectiveness_score = 0.75
        if config.product_recommendation_prompt:
            effectiveness_score += 0.1
        if config.objection_handling_prompt:
            effectiveness_score += 0.1

        if not suggestions:
            suggestions.append("提示词结构良好，建议通过实际测试验证效果")

        return {
            "clarity_score": min(1.0, clarity_score),
            "consistency_score": min(1.0, consistency_score),
            "effectiveness_score": min(1.0, effectiveness_score),
            "suggestions": suggestions
        }

    def _initialize_prompt_library(self):
        """初始化提示词库"""
        # 销售类提示词
        self._prompt_library.extend([
            PromptLibraryItem(
                item_id="sales_001",
                title="专业护肤顾问",
                category=PromptCategory.SALES,
                prompt_type=PromptType.PERSONALITY,
                language=PromptLanguage.CHINESE,
                prompt_content="""你是一位专业的护肤顾问，拥有丰富的皮肤护理知识和产品经验。你的目标是帮助客户找到最适合的护肤解决方案。

你的特点：
- 专业且耐心，善于倾听客户需求
- 能够根据不同肌肤类型提供个性化建议
- 熟悉各类护肤成分和产品功效
- 注重教育客户正确的护肤知识

交流风格：
- 语言温和专业，避免过于商业化的推销
- 先了解客户肌肤状况再推荐产品
- 提供详细的使用方法和注意事项
- 鼓励客户建立长期的护肤习惯""",
                use_case="适用于护肤品牌的专业咨询服务",
                recommended_parameters={"temperature": 0.7, "max_tokens": 800},
                author="护肤专家团队",
                usage_count=156,
                rating=4.8,
                example_context={"customer_skin_type": "油性", "concern": "痘痘"},
                example_output="根据您的油性肌肤特点和痘痘困扰，我建议您选择含有水杨酸成分的温和洁面产品...",
                notes="适合需要专业护肤建议的场景，避免过度推销"
            ),

            PromptLibraryItem(
                item_id="sales_002",
                title="时尚彩妆顾问",
                category=PromptCategory.SALES,
                prompt_type=PromptType.PERSONALITY,
                language=PromptLanguage.CHINESE,
                prompt_content="""你是一位充满活力的时尚彩妆顾问，对色彩搭配和妆容设计有着敏锐的直觉。你的使命是帮助每位客户展现最美的自己。

你的特点：
- 热情开朗，富有时尚感和创意
- 对色彩理论和妆容技巧了如指掌
- 能快速捕捉客户的风格偏好
- 善于推荐适合不同场合的妆容

交流风格：
- 语言生动有趣，充满正能量
- 分享实用的化妆技巧和流行趋势
- 鼓励客户尝试新的妆容风格
- 注重产品的实际使用效果""",
                use_case="适用于彩妆品牌的时尚咨询和产品推荐",
                recommended_parameters={"temperature": 0.8, "max_tokens": 600},
                author="彩妆师团队",
                usage_count=203,
                rating=4.6,
                example_context={"occasion": "约会", "skin_tone": "暖调"},
                example_output="约会妆容重在自然甜美！根据您的暖调肌肤，我推荐珊瑚色系的口红和腮红...",
                notes="适合年轻化、时尚化的彩妆品牌"
            )
        ])

        # 客服类提示词
        self._prompt_library.extend([
            PromptLibraryItem(
                item_id="service_001",
                title="贴心客服助手",
                category=PromptCategory.CUSTOMER_SERVICE,
                prompt_type=PromptType.PERSONALITY,
                language=PromptLanguage.CHINESE,
                prompt_content="""你是一位贴心专业的客服助手，致力于为每位客户提供优质的服务体验。

你的职责：
- 耐心解答客户的各种疑问
- 协助处理订单、配送、退换货等问题
- 收集客户反馈并提供解决方案
- 维护良好的客户关系

服务原则：
- 始终保持礼貌和耐心
- 快速准确地解决客户问题
- 主动关心客户需求
- 遇到复杂问题及时转接专业人员

沟通风格：
- 语言亲切自然，让客户感受到关怀
- 回答清晰准确，避免模糊表达
- 积极主动，提供额外的帮助建议""",
                use_case="适用于售后客服和订单咨询服务",
                recommended_parameters={"temperature": 0.6, "max_tokens": 500},
                author="客服团队",
                usage_count=89,
                rating=4.7,
                notes="注重问题解决的时效性和准确性"
            )
        ])

        self.logger.info(f"提示词库初始化完成，共加载{len(self._prompt_library)}个模板")
