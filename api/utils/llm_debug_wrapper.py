"""
LLM调试包装器工具

用于拦截和记录LLM调用的详细输入输出信息，
方便开发调试和Prompt优化。
"""

from typing import Any

class LLMDebugWrapper:
    """
    LLMClient的调试包装器
    
    拦截 completions 和 responses 方法调用，
    记录完整的 prompt input (system, role-level) 和 output。
    """
    def __init__(self, client: Any, node_name: str, logger: Any):
        self.client = client
        self.node_name = node_name
        self.logger = logger

    def __getattr__(self, name: str) -> Any:
        # 代理其他属性和方法到原始client
        return getattr(self.client, name)

    async def completions(self, request: Any) -> Any:
        self._log_request(request, "Completions")
        response = await self.client.completions(request)
        self._log_response(response, "Completions")
        return response

    async def responses(self, request: Any) -> Any:
        self._log_request(request, "Responses")
        response = await self.client.responses(request)
        self._log_response(response, "Responses")
        return response

    def _log_request(self, request: Any, method_type: str):
        try:
            log_msg = [f"\n[DEBUG] Node: {self.node_name} | Method: {method_type} | Input:"]
            
            # 记录 System Prompt 和 Input (针对 ResponseMessageRequest)
            if hasattr(request, "system_prompt") and request.system_prompt:
                 log_msg.append(f"  [SYSTEM]: {request.system_prompt}")
            
            if hasattr(request, "input") and request.input:
                 log_msg.append(f"  [INPUT]: {request.input}")

            # 记录 Messages (针对 CompletionsRequest)
            if hasattr(request, "messages"):
                messages = request.messages
                # 处理 messages 是列表的情况
                if isinstance(messages, list):
                    for msg in messages:
                        # 兼容 dict 和 Message 对象
                        role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", "unknown")
                        content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", "")
                        log_msg.append(f"  [{str(role).upper()}]: {content}")
                # 处理 messages 是单个对象的情况 (虽然不太常见，但防御性编程)
                elif messages:
                     log_msg.append(f"  [MESSAGES]: {messages}")
            
            self.logger.debug("\n".join(log_msg))
        except Exception as e:
            self.logger.warning(f"[DEBUG] Failed to log request for {self.node_name}: {e}")

    def _log_response(self, response: Any, method_type: str):
        try:
            content = getattr(response, "content", str(response))
            self.logger.debug(f"\n[DEBUG] Node: {self.node_name} | Method: {method_type} | Output:\n{content}")
        except Exception as e:
            self.logger.warning(f"[DEBUG] Failed to log response for {self.node_name}: {e}")

