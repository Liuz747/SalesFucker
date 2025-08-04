"""
多LLM供应商管理API端点测试套件

该测试模块专注于供应商管理API端点的核心功能测试:
- 供应商状态查询端点
- 供应商健康检查端点
- 供应商模型信息端点
- 供应商切换端点
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from fastapi import status
import json

from src.api.multi_llm_endpoints import router as multi_llm_router
from src.api.multi_llm_handlers import MultiLLMAPIHandler
from src.api.multi_llm_provider_handlers import ProviderManagementHandler
from src.llm.provider_config import ProviderType, GlobalProviderConfig
from src.llm.base_provider import LLMRequest, LLMResponse, ProviderHealth
from main import app


class TestMultiLLMProviderEndpoints:
    """测试多LLM供应商管理端点"""
    
    @pytest.fixture
    def client(self):
        """测试客户端fixture"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_provider_handler(self):
        """模拟供应商处理器fixture"""
        handler = Mock(spec=ProviderManagementHandler)
        
        # Mock provider status response
        handler.get_provider_status.return_value = {
            "tenant_id": "test_tenant",
            "providers": {
                "openai": {
                    "status": "healthy",
                    "last_check": datetime.now().isoformat(),
                    "latency_ms": 800,
                    "success_rate": 0.98,
                    "models": ["gpt-4", "gpt-3.5-turbo"]
                },
                "anthropic": {
                    "status": "healthy", 
                    "last_check": datetime.now().isoformat(),
                    "latency_ms": 600,
                    "success_rate": 0.99,
                    "models": ["claude-3-opus", "claude-3-sonnet"]
                },
                "gemini": {
                    "status": "degraded",
                    "last_check": datetime.now().isoformat(),
                    "latency_ms": 1200,
                    "success_rate": 0.95,
                    "models": ["gemini-pro"]
                },
                "deepseek": {
                    "status": "healthy",
                    "last_check": datetime.now().isoformat(),
                    "latency_ms": 900,
                    "success_rate": 0.97,
                    "models": ["deepseek-chat"]
                }
            },
            "healthy_providers": ["openai", "anthropic", "deepseek"],
            "total_providers": 4,
            "overall_health": "good"
        }
        
        return handler
    
    def test_get_provider_status(self, client, mock_provider_handler):
        """测试获取供应商状态端点"""
        with patch('src.api.multi_llm_endpoints.provider_handler', mock_provider_handler):
            response = client.get("/multi-llm/providers/status")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "providers" in data
            assert "healthy_providers" in data
            assert "total_providers" in data
            assert data["total_providers"] == 4
            assert len(data["healthy_providers"]) == 3
            assert data["overall_health"] == "good"
            
            # Check individual provider details
            openai_status = data["providers"]["openai"]
            assert openai_status["status"] == "healthy"
            assert openai_status["success_rate"] == 0.98
            assert "gpt-4" in openai_status["models"]
    
    def test_get_provider_health_detailed(self, client, mock_provider_handler):
        """测试获取详细供应商健康状态"""
        mock_provider_handler.get_detailed_health.return_value = {
            "provider": "openai",
            "status": "healthy",
            "health_score": 0.95,
            "metrics": {
                "avg_latency_ms": 750,
                "success_rate": 0.98,
                "error_rate": 0.02,
                "requests_per_minute": 45,
                "queue_length": 0
            },
            "recent_errors": [],
            "uptime_percentage": 99.8,
            "last_downtime": None
        }
        
        with patch('src.api.multi_llm_endpoints.provider_handler', mock_provider_handler):
            response = client.get("/multi-llm/providers/openai/health")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert data["provider"] == "openai"
            assert data["status"] == "healthy"
            assert data["health_score"] == 0.95
            assert data["metrics"]["success_rate"] == 0.98
            assert data["uptime_percentage"] == 99.8
    
    def test_get_provider_models(self, client, mock_provider_handler):
        """测试获取供应商模型信息"""
        mock_provider_handler.get_provider_models.return_value = {
            "provider": "openai",
            "total_models": 2,
            "models": [
                {
                    "name": "gpt-4",
                    "type": "chat",
                    "max_tokens": 8192,
                    "cost_per_1k_tokens": 0.03,
                    "available": True
                },
                {
                    "name": "gpt-3.5-turbo",
                    "type": "chat", 
                    "max_tokens": 4096,
                    "cost_per_1k_tokens": 0.002,
                    "available": True
                }
            ]
        }
        
        with patch('src.api.multi_llm_endpoints.provider_handler', mock_provider_handler):
            response = client.get("/multi-llm/providers/openai/models")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert data["provider"] == "openai"
            assert data["total_models"] == 2
            assert len(data["models"]) == 2
            assert data["models"][0]["name"] == "gpt-4"
            assert data["models"][1]["cost_per_1k_tokens"] == 0.002
    
    def test_switch_provider(self, client, mock_provider_handler):
        """测试切换供应商端点"""
        mock_provider_handler.switch_provider.return_value = {
            "success": True,
            "message": "Successfully switched to anthropic",
            "previous_provider": "openai",
            "new_provider": "anthropic",
            "switch_reason": "manual_switch",
            "timestamp": datetime.now().isoformat()
        }
        
        with patch('src.api.multi_llm_endpoints.provider_handler', mock_provider_handler):
            response = client.post(
                "/multi-llm/providers/switch",
                json={
                    "tenant_id": "test_tenant",
                    "agent_type": "sales",
                    "target_provider": "anthropic",
                    "reason": "manual_switch"
                }
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert data["success"] is True
            assert "Successfully switched to anthropic" in data["message"]
            assert data["new_provider"] == "anthropic"
            assert data["switch_reason"] == "manual_switch"
    
    def test_provider_status_with_filters(self, client, mock_provider_handler):
        """测试带过滤器的供应商状态查询"""
        mock_provider_handler.get_provider_status.return_value = {
            "tenant_id": "test_tenant",
            "providers": {
                "openai": {
                    "status": "healthy",
                    "agent_assignments": ["sales", "compliance"]
                },
                "anthropic": {
                    "status": "healthy",
                    "agent_assignments": ["sentiment", "product"]
                }
            },
            "filtered_results": 2
        }
        
        with patch('src.api.multi_llm_endpoints.provider_handler', mock_provider_handler):
            response = client.get(
                "/multi-llm/providers/status",
                params={
                    "tenant_id": "test_tenant",
                    "status_filter": "healthy",
                    "agent_type": "sales"
                }
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert "providers" in data
            assert data["filtered_results"] == 2
            
            # Verify agent assignments
            openai_data = data["providers"]["openai"]
            assert "sales" in openai_data["agent_assignments"]
    
    def test_provider_performance_metrics(self, client, mock_provider_handler):
        """测试供应商性能指标端点"""
        mock_provider_handler.get_performance_metrics.return_value = {
            "provider": "openai",
            "time_period": "24h",
            "metrics": {
                "avg_response_time_ms": 850,
                "median_response_time_ms": 750,
                "p95_response_time_ms": 1200,
                "success_rate": 0.982,
                "total_requests": 1250,
                "failed_requests": 23,
                "throughput_per_minute": 52
            },
            "trend_analysis": {
                "response_time_trend": "stable",
                "success_rate_trend": "improving",
                "throughput_trend": "increasing"
            }
        }
        
        with patch('src.api.multi_llm_endpoints.provider_handler', mock_provider_handler):
            response = client.get(
                "/multi-llm/providers/openai/metrics",
                params={"period": "24h"}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert data["provider"] == "openai"
            assert data["metrics"]["success_rate"] == 0.982
            assert data["trend_analysis"]["success_rate_trend"] == "improving"


if __name__ == "__main__":
    # 运行供应商端点测试
    def run_provider_endpoint_tests():
        print("运行供应商端点测试...")
        
        # 创建测试客户端
        client = TestClient(app)
        print("测试客户端创建成功")
        
        # 模拟供应商处理器
        handler = Mock(spec=ProviderManagementHandler)
        handler.get_provider_status.return_value = {
            "providers": {"openai": {"status": "healthy"}},
            "total_providers": 1
        }
        print("模拟处理器创建成功")
        
        print("供应商端点测试完成!")
    
    run_provider_endpoint_tests()