"""
智能体管理业务逻辑处理器

该模块实现智能体管理相关的业务逻辑，包括智能体测试、状态查询、
配置管理等功能。负责协调智能体注册表、编排器和其他相关服务。

主要功能:
- 智能体列表查询和筛选
- 智能体状态监控
- 智能体测试和验证
- 智能体配置更新
- 批量操作支持
"""

from typing import Dict, Any, Optional, List
import asyncio
import logging
from datetime import datetime

from src.core import get_orchestrator
from src.agents import agent_registry, AgentRegistry
from src.utils import get_component_logger
from ..schemas.agents import (
    AgentTestRequest,
    AgentBatchTestRequest,
    AgentConfigUpdateRequest,
    AgentStatusResponse,
    AgentListResponse,
    AgentTestResponse,
    AgentBatchTestResponse,
    AgentOperationResponse
)
from ..schemas.requests import PaginationRequest
from ..exceptions import (
    AgentNotFoundException,
    AgentUnavailableException,
    ValidationException
)

logger = get_component_logger(__name__, "AgentHandler")


class AgentHandler:
    """智能体管理业务逻辑处理器"""
    
    def __init__(self):
        """初始化处理器"""
        self.registry = agent_registry
        self.logger = logger
    
    async def list_agents(
        self,
        tenant_id: str,
        pagination: PaginationRequest,
        filters: Optional[Dict[str, Any]] = None,
        registry: Optional[AgentRegistry] = None
    ) -> AgentListResponse:
        """
        获取智能体列表
        
        Args:
            tenant_id: 租户ID
            pagination: 分页参数
            filters: 筛选条件
            registry: 智能体注册表
            
        Returns:
            智能体列表响应
        """
        try:
            used_registry = registry or self.registry
            filters = filters or {}
            
            # 获取租户的所有智能体
            tenant_agents = [
                agent for agent_id, agent in used_registry.agents.items()
                if agent.tenant_id == tenant_id
            ]
            
            # 应用筛选条件
            if filters.get("agent_type"):
                tenant_agents = [
                    agent for agent in tenant_agents
                    if agent.agent_type == filters["agent_type"]
                ]
            
            if filters.get("status"):
                status_filter = filters["status"]
                tenant_agents = [
                    agent for agent in tenant_agents
                    if (agent.is_active if status_filter == "active" else not agent.is_active)
                ]
            
            # 计算分页
            total = len(tenant_agents)
            start_idx = (pagination.page - 1) * pagination.size
            end_idx = start_idx + pagination.size
            paginated_agents = tenant_agents[start_idx:end_idx]
            
            # 构建响应数据
            agent_list = []
            for agent in paginated_agents:
                agent_status = AgentStatusResponse(
                    agent_id=agent.agent_id,
                    agent_type=agent.agent_type,
                    tenant_id=agent.tenant_id,
                    is_active=agent.is_active,
                    health_status="healthy" if agent.is_active else "inactive",
                    messages_processed=agent.processing_stats.get("messages_processed", 0),
                    errors=agent.processing_stats.get("errors", 0),
                    last_activity=agent.processing_stats.get("last_activity"),
                    performance_metrics={
                        "avg_response_time": agent.processing_stats.get("avg_response_time", 0),
                        "success_rate": agent.processing_stats.get("success_rate", 100)
                    },
                    recent_errors=[]
                )
                agent_list.append(agent_status)
            
            return AgentListResponse(
                data=agent_list,
                total=total,
                page=pagination.page,
                size=pagination.size,
                has_next=end_idx < total
            )
            
        except Exception as e:
            self.logger.error(f"获取智能体列表失败: {e}", exc_info=True)
            raise ValidationException(f"获取智能体列表失败: {str(e)}")
    
    async def get_agent_status(
        self,
        agent_id: str,
        tenant_id: str,
        registry: Optional[AgentRegistry] = None
    ) -> AgentStatusResponse:
        """
        获取特定智能体的状态
        
        Args:
            agent_id: 智能体ID
            tenant_id: 租户ID
            registry: 智能体注册表
            
        Returns:
            智能体状态响应
        """
        try:
            used_registry = registry or self.registry
            
            # 查找智能体
            agent = used_registry.agents.get(agent_id)
            if not agent:
                raise AgentNotFoundException(agent_id)
            
            # 验证租户权限
            if agent.tenant_id != tenant_id:
                raise AgentNotFoundException(agent_id)
            
            return AgentStatusResponse(
                agent_id=agent.agent_id,
                agent_type=agent.agent_type,
                tenant_id=agent.tenant_id,
                is_active=agent.is_active,
                health_status="healthy" if agent.is_active else "inactive",
                messages_processed=agent.processing_stats.get("messages_processed", 0),
                errors=agent.processing_stats.get("errors", 0),
                last_activity=agent.processing_stats.get("last_activity"),
                performance_metrics={
                    "avg_response_time": agent.processing_stats.get("avg_response_time", 0),
                    "success_rate": agent.processing_stats.get("success_rate", 100),
                    "total_requests": agent.processing_stats.get("total_requests", 0)
                },
                recent_errors=agent.processing_stats.get("recent_errors", [])
            )
            
        except AgentNotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"获取智能体状态失败 {agent_id}: {e}", exc_info=True)
            raise ValidationException(f"获取智能体状态失败: {str(e)}")
    
    async def test_agent(
        self,
        agent_id: str,
        test_request: AgentTestRequest,
        tenant_id: str,
        registry: Optional[AgentRegistry] = None
    ) -> AgentTestResponse:
        """
        测试特定智能体
        
        Args:
            agent_id: 智能体ID
            test_request: 测试请求
            tenant_id: 租户ID
            registry: 智能体注册表
            
        Returns:
            智能体测试响应
        """
        try:
            used_registry = registry or self.registry
            
            # 查找智能体
            agent = used_registry.agents.get(agent_id)
            if not agent:
                raise AgentNotFoundException(agent_id)
            
            # 验证租户权限
            if agent.tenant_id != tenant_id:
                raise AgentNotFoundException(agent_id)
            
            # 检查智能体是否可用
            if not agent.is_active:
                raise AgentUnavailableException(agent_id)
            
            # 执行测试
            start_time = datetime.now()
            
            try:
                # 调用智能体处理消息
                result = await agent.process_message(
                    message=test_request.test_message,
                    context=test_request.context or {}
                )
                
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds() * 1000
                
                return AgentTestResponse(
                    test_id=f"test_{agent_id}_{int(start_time.timestamp())}",
                    agent_id=agent_id,
                    test_type=test_request.test_type,
                    test_message=test_request.test_message,
                    agent_response=result.get("response", ""),
                    success=True,
                    response_time_ms=response_time,
                    test_results={
                        "status": "passed",
                        "response_data": result,
                        "performance": {
                            "response_time": response_time,
                            "memory_usage": result.get("memory_usage", 0)
                        }
                    },
                    metadata={
                        "agent_type": agent.agent_type,
                        "test_timestamp": start_time.isoformat(),
                        "test_environment": "api_test"
                    }
                )
                
            except Exception as processing_error:
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds() * 1000
                
                return AgentTestResponse(
                    test_id=f"test_{agent_id}_{int(start_time.timestamp())}",
                    agent_id=agent_id,
                    test_type=test_request.test_type,
                    test_message=test_request.test_message,
                    agent_response="",
                    success=False,
                    response_time_ms=response_time,
                    error_message=str(processing_error),
                    test_results={
                        "status": "failed",
                        "error": str(processing_error),
                        "performance": {
                            "response_time": response_time
                        }
                    },
                    metadata={
                        "agent_type": agent.agent_type,
                        "test_timestamp": start_time.isoformat(),
                        "error_type": type(processing_error).__name__
                    }
                )
                
        except (AgentNotFoundException, AgentUnavailableException):
            raise
        except Exception as e:
            self.logger.error(f"智能体测试失败 {agent_id}: {e}", exc_info=True)
            raise ValidationException(f"智能体测试失败: {str(e)}")
    
    async def batch_test_agents(
        self,
        batch_request: AgentBatchTestRequest,
        tenant_id: str,
        registry: Optional[AgentRegistry] = None
    ) -> AgentBatchTestResponse:
        """
        批量测试多个智能体
        
        Args:
            batch_request: 批量测试请求
            tenant_id: 租户ID
            registry: 智能体注册表
            
        Returns:
            批量测试响应
        """
        try:
            batch_id = f"batch_{tenant_id}_{int(datetime.now().timestamp())}"
            test_results = []
            failed_tests = []
            
            # 准备测试任务
            test_tasks = []
            for agent_test in batch_request.agent_tests:
                test_tasks.append(
                    self._single_agent_test(
                        agent_test.agent_id,
                        agent_test,
                        tenant_id,
                        registry
                    )
                )
            
            # 执行测试（并行或串行）
            if batch_request.parallel_execution:
                results = await asyncio.gather(*test_tasks, return_exceptions=True)
            else:
                results = []
                for task in test_tasks:
                    try:
                        result = await task
                        results.append(result)
                    except Exception as e:
                        results.append(e)
            
            # 处理结果
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_tests.append({
                        "agent_id": batch_request.agent_tests[i].agent_id,
                        "error": str(result)
                    })
                else:
                    test_results.append(result)
            
            # 计算统计信息
            total_tests = len(batch_request.agent_tests)
            successful_tests = len(test_results)
            failed_test_count = len(failed_tests)
            
            return AgentBatchTestResponse(
                batch_id=batch_id,
                total_tests=total_tests,
                successful_tests=successful_tests,
                failed_tests=failed_test_count,
                test_results=test_results,
                execution_summary={
                    "parallel_execution": batch_request.parallel_execution,
                    "total_duration_ms": sum(r.response_time_ms for r in test_results),
                    "average_response_time": (
                        sum(r.response_time_ms for r in test_results) / len(test_results)
                        if test_results else 0
                    ),
                    "success_rate": (successful_tests / total_tests * 100) if total_tests > 0 else 0
                },
                failed_test_details=failed_tests if failed_tests else None
            )
            
        except Exception as e:
            self.logger.error(f"批量测试失败: {e}", exc_info=True)
            raise ValidationException(f"批量测试失败: {str(e)}")
    
    async def _single_agent_test(
        self,
        agent_id: str,
        test_request: AgentTestRequest,
        tenant_id: str,
        registry: Optional[AgentRegistry] = None
    ) -> AgentTestResponse:
        """执行单个智能体测试的内部方法"""
        return await self.test_agent(agent_id, test_request, tenant_id, registry)
    
    async def update_agent_config(
        self,
        agent_id: str,
        config_request: AgentConfigUpdateRequest,
        tenant_id: str,
        registry: Optional[AgentRegistry] = None
    ) -> AgentOperationResponse:
        """
        更新智能体配置
        
        Args:
            agent_id: 智能体ID
            config_request: 配置更新请求
            tenant_id: 租户ID
            registry: 智能体注册表
            
        Returns:
            操作响应
        """
        try:
            used_registry = registry or self.registry
            
            # 查找智能体
            agent = used_registry.agents.get(agent_id)
            if not agent:
                raise AgentNotFoundException(agent_id)
            
            # 验证租户权限
            if agent.tenant_id != tenant_id:
                raise AgentNotFoundException(agent_id)
            
            # 更新配置
            if hasattr(agent, 'update_config'):
                await agent.update_config(
                    config_request.config_updates,
                    merge_mode=config_request.merge_mode
                )
            
            return AgentOperationResponse(
                operation_id=f"config_update_{agent_id}_{int(datetime.now().timestamp())}",
                agent_id=agent_id,
                operation_type="config_update",
                success=True,
                message=f"智能体 {agent_id} 配置更新成功",
                operation_details={
                    "updated_fields": list(config_request.config_updates.keys()),
                    "merge_mode": config_request.merge_mode,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except AgentNotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"更新智能体配置失败 {agent_id}: {e}", exc_info=True)
            raise ValidationException(f"更新智能体配置失败: {str(e)}")
    
    async def activate_agent(
        self,
        agent_id: str,
        tenant_id: str,
        registry: Optional[AgentRegistry] = None
    ) -> AgentOperationResponse:
        """激活智能体"""
        return await self._agent_lifecycle_operation(
            agent_id, tenant_id, "activate", registry
        )
    
    async def deactivate_agent(
        self,
        agent_id: str,
        tenant_id: str,
        registry: Optional[AgentRegistry] = None
    ) -> AgentOperationResponse:
        """停用智能体"""
        return await self._agent_lifecycle_operation(
            agent_id, tenant_id, "deactivate", registry
        )
    
    async def restart_agent(
        self,
        agent_id: str,
        tenant_id: str,
        registry: Optional[AgentRegistry] = None
    ) -> AgentOperationResponse:
        """重启智能体"""
        return await self._agent_lifecycle_operation(
            agent_id, tenant_id, "restart", registry
        )
    
    async def _agent_lifecycle_operation(
        self,
        agent_id: str,
        tenant_id: str,
        operation: str,
        registry: Optional[AgentRegistry] = None
    ) -> AgentOperationResponse:
        """执行智能体生命周期操作的内部方法"""
        try:
            used_registry = registry or self.registry
            
            # 查找智能体
            agent = used_registry.agents.get(agent_id)
            if not agent:
                raise AgentNotFoundException(agent_id)
            
            # 验证租户权限
            if agent.tenant_id != tenant_id:
                raise AgentNotFoundException(agent_id)
            
            # 执行操作
            if operation == "activate":
                agent.is_active = True
                message = f"智能体 {agent_id} 已激活"
            elif operation == "deactivate":
                agent.is_active = False
                message = f"智能体 {agent_id} 已停用"
            elif operation == "restart":
                agent.is_active = False
                await asyncio.sleep(0.1)  # 短暂停顿
                agent.is_active = True
                message = f"智能体 {agent_id} 已重启"
            else:
                raise ValidationException(f"不支持的操作: {operation}")
            
            return AgentOperationResponse(
                operation_id=f"{operation}_{agent_id}_{int(datetime.now().timestamp())}",
                agent_id=agent_id,
                operation_type=operation,
                success=True,
                message=message,
                operation_details={
                    "operation": operation,
                    "timestamp": datetime.now().isoformat(),
                    "new_status": "active" if agent.is_active else "inactive"
                }
            )
            
        except (AgentNotFoundException, ValidationException):
            raise
        except Exception as e:
            self.logger.error(f"智能体 {operation} 操作失败 {agent_id}: {e}", exc_info=True)
            raise ValidationException(f"智能体 {operation} 操作失败: {str(e)}")
    
    async def get_tenant_registry_status(
        self,
        tenant_id: str,
        registry: Optional[AgentRegistry] = None
    ) -> Dict[str, Any]:
        """获取租户智能体注册状态（遗留兼容方法）"""
        try:
            used_registry = registry or self.registry
            
            # 获取租户智能体
            tenant_agents = [
                agent for agent_id, agent in used_registry.agents.items()
                if agent.tenant_id == tenant_id
            ]
            
            agent_details = []
            for agent in tenant_agents:
                agent_details.append({
                    "agent_id": agent.agent_id,
                    "agent_type": agent.agent_type,
                    "is_active": agent.is_active,
                    "messages_processed": agent.processing_stats.get("messages_processed", 0),
                    "errors": agent.processing_stats.get("errors", 0)
                })
            
            return {
                "tenant_id": tenant_id,
                "total_agents": len(tenant_agents),
                "active_agents": len([a for a in tenant_agents if a.is_active]),
                "agent_details": agent_details
            }
            
        except Exception as e:
            self.logger.error(f"获取租户注册状态失败 {tenant_id}: {e}", exc_info=True)
            raise ValidationException(f"获取租户注册状态失败: {str(e)}")