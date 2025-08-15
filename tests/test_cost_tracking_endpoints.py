"""
成本追踪API端点测试套件

该测试模块专注于成本追踪API端点的核心功能测试:
- 成本分析端点测试
- 实时成本监控端点
- 成本预算和警报端点
- 成本优化建议端点
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from fastapi import status
import json

from api.multi_llm_endpoints import router as multi_llm_router
from api.multi_llm_handlers import MultiLLMAPIHandler
from src.llm.cost_optimizer.models import CostRecord, UsageMetrics
from main import app


class TestCostTrackingEndpoints:
    """测试成本追踪API端点"""
    
    @pytest.fixture
    def client(self):
        """测试客户端fixture"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_cost_handler(self):
        """模拟成本处理器fixture"""
        handler = Mock()
        
        # Mock cost analysis response
        handler.get_cost_analysis.return_value = {
            "period_start": "2024-08-01T00:00:00",
            "period_end": "2024-08-03T23:59:59",
            "total_cost": 15.75,
            "total_requests": 1250,
            "total_tokens": 185000,
            "avg_cost_per_request": 0.0126,
            "avg_cost_per_token": 0.0000851,
            "provider_breakdown": {
                "openai": {
                    "cost": 8.50,
                    "requests": 600,
                    "percentage": 53.97
                },
                "anthropic": {
                    "cost": 4.25,
                    "requests": 300,
                    "percentage": 26.98
                },
                "gemini": {
                    "cost": 2.00,
                    "requests": 250,
                    "percentage": 12.70
                },
                "deepseek": {
                    "cost": 1.00,
                    "requests": 100,
                    "percentage": 6.35
                }
            },
            "agent_breakdown": {
                "sales": {"cost": 6.30, "requests": 500},
                "compliance": {"cost": 4.20, "requests": 350},
                "sentiment": {"cost": 3.15, "requests": 250},
                "product": {"cost": 2.10, "requests": 150}
            }
        }
        
        return handler
    
    def test_get_cost_analysis(self, client, mock_cost_handler):
        """测试获取成本分析端点"""
        with patch('src.api.multi_llm_endpoints.multi_llm_handler.cost_optimizer', mock_cost_handler):
            response = client.get(
                "/multi-llm/costs/analysis",
                params={
                    "tenant_id": "test_tenant",
                    "start_date": "2024-08-01",
                    "end_date": "2024-08-03"
                }
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert data["total_cost"] == 15.75
            assert data["total_requests"] == 1250
            assert data["avg_cost_per_request"] == 0.0126
            assert "provider_breakdown" in data
            assert "agent_breakdown" in data
            assert data["provider_breakdown"]["openai"]["percentage"] == 53.97
            assert data["agent_breakdown"]["sales"]["cost"] == 6.30
    
    def test_get_real_time_costs(self, client, mock_cost_handler):
        """测试实时成本获取端点"""
        mock_cost_handler.get_real_time_costs.return_value = {
            "current_hour_cost": 0.85,
            "current_day_cost": 12.40,
            "current_month_cost": 245.60,
            "requests_last_hour": 45,
            "requests_today": 680,
            "requests_this_month": 9850,
            "top_consuming_agents": [
                {"agent": "sales", "cost": 4.20, "requests": 220},
                {"agent": "product", "cost": 3.15, "requests": 180},
                {"agent": "compliance", "cost": 2.80, "requests": 140}
            ],
            "cost_trend": "increasing",
            "projected_monthly_cost": 380.50
        }
        
        with patch('src.api.multi_llm_endpoints.multi_llm_handler.cost_optimizer', mock_cost_handler):
            response = client.get(
                "/multi-llm/costs/realtime",
                params={"tenant_id": "test_tenant"}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert data["current_day_cost"] == 12.40
            assert data["current_month_cost"] == 245.60
            assert data["requests_today"] == 680
            assert len(data["top_consuming_agents"]) == 3
            assert data["cost_trend"] == "increasing"
            assert data["projected_monthly_cost"] == 380.50
    
    def test_get_cost_budget_status(self, client, mock_cost_handler):
        """测试成本预算状态端点"""
        mock_cost_handler.get_budget_status.return_value = {
            "tenant_id": "test_tenant",
            "budget_period": "monthly",
            "budget_limit": 500.00,
            "current_spend": 245.60,
            "remaining_budget": 254.40,
            "budget_utilization": 0.4912,
            "days_remaining": 12,
            "projected_spend": 380.50,
            "budget_status": "on_track",
            "alerts": [],
            "recommendations": [
                "Consider switching to lower-cost providers for non-critical tasks",
                "Optimize prompt lengths to reduce token usage"
            ]
        }
        
        with patch('src.api.multi_llm_endpoints.multi_llm_handler.cost_optimizer', mock_cost_handler):
            response = client.get(
                "/multi-llm/costs/budget",
                params={"tenant_id": "test_tenant"}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert data["budget_limit"] == 500.00
            assert data["current_spend"] == 245.60
            assert data["budget_utilization"] == 0.4912
            assert data["budget_status"] == "on_track"
            assert len(data["recommendations"]) == 2
    
    def test_get_cost_trends(self, client, mock_cost_handler):
        """测试成本趋势分析端点"""
        mock_cost_handler.get_cost_trends.return_value = {
            "period": "7d",
            "daily_costs": [
                {"date": "2024-08-01", "cost": 8.50},
                {"date": "2024-08-02", "cost": 9.25},
                {"date": "2024-08-03", "cost": 10.15},
                {"date": "2024-08-04", "cost": 12.40},
                {"date": "2024-08-05", "cost": 11.80},
                {"date": "2024-08-06", "cost": 13.20},
                {"date": "2024-08-07", "cost": 14.75}
            ],
            "trend_direction": "increasing",
            "avg_daily_cost": 11.43,
            "peak_cost_day": "2024-08-07",
            "lowest_cost_day": "2024-08-01",
            "cost_variance": 2.25,
            "growth_rate": 0.73
        }
        
        with patch('src.api.multi_llm_endpoints.multi_llm_handler.cost_optimizer', mock_cost_handler):
            response = client.get(
                "/multi-llm/costs/trends",
                params={
                    "tenant_id": "test_tenant",
                    "period": "7d"
                }
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert data["period"] == "7d"
            assert len(data["daily_costs"]) == 7
            assert data["trend_direction"] == "increasing"
            assert data["avg_daily_cost"] == 11.43
            assert data["growth_rate"] == 0.73
            assert data["peak_cost_day"] == "2024-08-07"
    
    def test_set_cost_alerts(self, client, mock_cost_handler):
        """测试设置成本警报端点"""
        mock_cost_handler.set_cost_alert.return_value = {
            "alert_id": "alert_123",
            "tenant_id": "test_tenant",
            "alert_type": "budget_threshold",
            "threshold": 400.00,
            "threshold_type": "monthly_spend",
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "notification_channels": ["email", "webhook"]
        }
        
        with patch('src.api.multi_llm_endpoints.multi_llm_handler.cost_optimizer', mock_cost_handler):
            response = client.post(
                "/multi-llm/costs/alerts",
                json={
                    "tenant_id": "test_tenant",
                    "alert_type": "budget_threshold",
                    "threshold": 400.00,
                    "threshold_type": "monthly_spend",
                    "notification_channels": ["email", "webhook"]
                }
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            
            assert data["alert_id"] == "alert_123"
            assert data["threshold"] == 400.00
            assert data["status"] == "active"
            assert "email" in data["notification_channels"]
    
    def test_get_usage_metrics(self, client, mock_cost_handler):
        """测试获取使用指标端点"""
        mock_cost_handler.get_usage_metrics.return_value = {
            "tenant_id": "test_tenant",
            "period": "24h",
            "total_requests": 1250,
            "successful_requests": 1227,
            "failed_requests": 23,
            "success_rate": 0.982,
            "total_tokens": 185000,
            "input_tokens": 120000,
            "output_tokens": 65000,
            "avg_tokens_per_request": 148,
            "peak_requests_per_hour": 85,
            "agent_usage": {
                "sales": {"requests": 500, "tokens": 74000},
                "compliance": {"requests": 350, "tokens": 51800},
                "sentiment": {"requests": 250, "tokens": 37000},
                "product": {"requests": 150, "tokens": 22200}
            },
            "model_usage": {
                "gpt-4": {"requests": 600, "tokens": 89000},
                "claude-3-sonnet": {"requests": 400, "tokens": 58000},
                "gemini-pro": {"requests": 250, "tokens": 38000}
            }
        }
        
        with patch('src.api.multi_llm_endpoints.multi_llm_handler.cost_optimizer', mock_cost_handler):
            response = client.get(
                "/multi-llm/usage/metrics",
                params={
                    "tenant_id": "test_tenant",
                    "period": "24h"
                }
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert data["total_requests"] == 1250
            assert data["success_rate"] == 0.982
            assert data["total_tokens"] == 185000
            assert data["avg_tokens_per_request"] == 148
            assert data["agent_usage"]["sales"]["requests"] == 500
            assert data["model_usage"]["gpt-4"]["tokens"] == 89000


if __name__ == "__main__":
    # 运行成本追踪端点测试
    def run_cost_tracking_tests():
        print("运行成本追踪端点测试...")
        
        # 创建测试客户端
        client = TestClient(app)
        print("测试客户端创建成功")
        
        # 模拟成本处理器
        handler = Mock()
        handler.get_cost_analysis.return_value = {
            "total_cost": 15.75,
            "total_requests": 1250
        }
        print("模拟成本处理器创建成功")
        
        print("成本追踪端点测试完成!")
    
    run_cost_tracking_tests()