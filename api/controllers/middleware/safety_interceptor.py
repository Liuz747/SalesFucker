"""
安全审查中间件

该中间件对所有请求和响应进行安全审查，确保内容合规。
特别针对化妆品行业的法规要求进行定制化审查。

核心功能:
- 请求内容安全审查
- 响应内容合规检查
- 敏感信息过滤
- 审查日志记录
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Any, List
import json
import re
import logging

from utils import get_component_logger

logger = get_component_logger(__name__, "SafetyInterceptor")


class SafetyInterceptor(BaseHTTPMiddleware):
    """
    安全审查中间件
    
    对API请求和响应进行安全审查，确保内容符合化妆品行业规范。
    """
    
    def __init__(self, app):
        super().__init__(app)
        
        # 违禁词列表（化妆品行业特定）
        self.forbidden_words = [
            "医用", "治疗", "药用", "医疗级",
            "治愈", "疗效", "临床验证", "临床试验",
            "抗癌", "防癌", "抗病毒", "杀菌",
            "速效", "立即见效", "一次见效",
            "永久", "终生", "100%有效"
        ]
        
        # 需要审查的路径模式
        self.review_paths = [
            r"/api/v1/conversations.*",
            r"/api/v1/agents.*",
            r"/api/v1/multimodal.*"
        ]
        
        # 敏感信息正则模式
        self.sensitive_patterns = [
            r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",  # 信用卡号
            r"\b\d{11,15}\b",  # 手机号
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"  # 邮箱
        ]
    
    async def dispatch(self, request: Request, call_next):
        """
        中间件处理逻辑
        
        参数:
            request: HTTP请求
            call_next: 下一个中间件或处理器
            
        返回:
            Response: HTTP响应
        """
        # 检查是否需要审查此路径
        if not self._should_review_path(request.url.path):
            return await call_next(request)
        
        # 审查请求内容
        request_body = await self._get_request_body(request)
        if request_body:
            safety_result = await self._review_content(request_body, "request")
            if not safety_result["safe"]:
                return await self._create_safety_violation_response(safety_result)
        
        # 处理请求
        response = await call_next(request)
        
        # 审查响应内容
        if response.status_code == 200:
            response_body = await self._get_response_body(response)
            if response_body:
                safety_result = await self._review_content(response_body, "response")
                if not safety_result["safe"]:
                    return await self._create_safety_violation_response(safety_result)
        
        return response
    
    def _should_review_path(self, path: str) -> bool:
        """
        检查路径是否需要安全审查
        
        参数:
            path: 请求路径
            
        返回:
            bool: 是否需要审查
        """
        for pattern in self.review_paths:
            if re.match(pattern, path):
                return True
        return False
    
    async def _get_request_body(self, request: Request) -> Dict[str, Any]:
        """
        获取请求体内容
        
        参数:
            request: HTTP请求
            
        返回:
            Dict[str, Any]: 请求体内容
        """
        try:
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
                if body:
                    return json.loads(body.decode())
        except Exception as e:
            logger.warning(f"解析请求体失败: {e}")
        return {}
    
    async def _get_response_body(self, response: Response) -> Dict[str, Any]:
        """
        获取响应体内容
        
        参数:
            response: HTTP响应
            
        返回:
            Dict[str, Any]: 响应体内容
        """
        try:
            if hasattr(response, 'body'):
                body = response.body
                if body:
                    return json.loads(body.decode())
        except Exception as e:
            logger.warning(f"解析响应体失败: {e}")
        return {}
    
    async def _review_content(self, content: Dict[str, Any], content_type: str) -> Dict[str, Any]:
        """
        审查内容安全性
        
        参数:
            content: 要审查的内容
            content_type: 内容类型（request/response）
            
        返回:
            Dict[str, Any]: 审查结果
        """
        result = {
            "safe": True,
            "violations": [],
            "content_type": content_type
        }
        
        # 转换为文本进行审查
        text_content = self._extract_text_from_content(content)
        
        # 检查违禁词
        forbidden_violations = self._check_forbidden_words(text_content)
        if forbidden_violations:
            result["safe"] = False
            result["violations"].extend(forbidden_violations)
        
        # 检查敏感信息
        sensitive_violations = self._check_sensitive_info(text_content)
        if sensitive_violations:
            result["safe"] = False
            result["violations"].extend(sensitive_violations)
        
        # 记录审查结果
        if not result["safe"]:
            logger.warning(f"安全审查失败 - {content_type}: {result['violations']}")
        
        return result
    
    def _extract_text_from_content(self, content: Dict[str, Any]) -> str:
        """
        从结构化内容中提取文本
        
        参数:
            content: 结构化内容
            
        返回:
            str: 提取的文本
        """
        text_parts = []
        
        def extract_text(obj):
            if isinstance(obj, str):
                text_parts.append(obj)
            elif isinstance(obj, dict):
                for value in obj.values():
                    extract_text(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_text(item)
        
        extract_text(content)
        return " ".join(text_parts)
    
    def _check_forbidden_words(self, text: str) -> List[Dict[str, str]]:
        """
        检查违禁词
        
        参数:
            text: 要检查的文本
            
        返回:
            List[Dict[str, str]]: 违规信息列表
        """
        violations = []
        text_lower = text.lower()
        
        for word in self.forbidden_words:
            if word in text_lower:
                violations.append({
                    "type": "forbidden_word",
                    "word": word,
                    "message": f"包含违禁词: {word}"
                })
        
        return violations
    
    def _check_sensitive_info(self, text: str) -> List[Dict[str, str]]:
        """
        检查敏感信息
        
        参数:
            text: 要检查的文本
            
        返回:
            List[Dict[str, str]]: 违规信息列表
        """
        violations = []
        
        for pattern in self.sensitive_patterns:
            matches = re.findall(pattern, text)
            if matches:
                violations.append({
                    "type": "sensitive_info",
                    "pattern": pattern,
                    "message": f"包含敏感信息: {len(matches)}处"
                })
        
        return violations
    
    async def _create_safety_violation_response(self, safety_result: Dict[str, Any]) -> JSONResponse:
        """
        创建安全违规响应
        
        参数:
            safety_result: 安全审查结果
            
        返回:
            JSONResponse: 违规响应
        """
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "SAFETY_VIOLATION",
                    "message": "内容违反安全策略",
                    "details": {
                        "violations": safety_result["violations"],
                        "content_type": safety_result["content_type"]
                    }
                }
            }
        )