from collections.abc import Mapping

from starlette.exceptions import HTTPException


class BaseHTTPException(HTTPException):
    """
    HTTP异常基类

    继承Starlette的HTTPException，提供标准化的HTTP错误响应格式。
    所有需要返回HTTP错误响应的异常都应该继承此类。

    属性:
        error_code: 业务错误代码，子类应该重写此属性
        error_message: 错误描述，子类应该重写此属性
        data: 结构化的错误响应数据

    用法示例:
        class AgentNotFound(BaseHTTPException):
            error_code = 10011
            error_message = "AGENT_NOT_FOUND"
            status_code = 404

            def __init__(self, agent_id: str):
                super().__init__(detail=f"智能体 {agent_id} 不存在")
    """

    # 20000 代表 internal server error
    error_code: int = 200
    error_message: str = "SUCCESS"
    http_status_code: int = 500
    data: dict | None = None

    def __init__(self, detail: str | None = None, headers: Mapping[str, str] | None = None):
        super().__init__(self.http_status_code, detail, headers)

        self.data = {
            "code": self.error_code,
            "error": self.error_message,
            "message": self.detail
        }