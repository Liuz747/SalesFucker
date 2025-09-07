
from fastapi import status


class RespCode:
    code: int
    message: str
    http_code: int

    def __init__(self, code: int, message: str, http_code: int = 200):
        self.code = code  # 实例变量，存储名字
        self.message = message  # 实例变量，存储年龄
        self.http_code = http_code


tenant_id_not_equal_resp = RespCode(
    code=10011,
    # Tenant ID in URL and request body must match
    message="Tenant ID in URL and request body must match",
    http_code=400
)

internal_server_error_resp = RespCode(
    code=2000,
    message="Internal server error",
    http_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
)

database_not_available_resp = RespCode(
    code=20012,
    message="Database not available",
    http_code=status.HTTP_503_SERVICE_UNAVAILABLE
)

