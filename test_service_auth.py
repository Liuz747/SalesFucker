#!/usr/bin/env python3
"""
服务认证集成测试

测试完整的服务JWT认证流程：
1. 使用App-Key获取服务JWT token
2. 使用JWT token进行服务认证验证
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

from src.auth.jwt_auth import verify_service_jwt_token
from config.settings import settings
import jwt
from datetime import datetime, timezone, timedelta


async def test_service_jwt_flow():
    """测试服务JWT认证完整流程"""
    
    print("=== 服务JWT认证测试 ===")
    
    # 1. 模拟生成服务JWT token（相当于/auth/token端点的行为）
    print("\n1. 生成服务JWT token...")
    
    # 检查配置
    if not hasattr(settings, 'app_jwt_secret') or not settings.app_jwt_secret:
        print("❌ 错误：未配置 app_jwt_secret")
        return False
    
    if not hasattr(settings, 'app_jwt_issuer') or not settings.app_jwt_issuer:
        print("❌ 错误：未配置 app_jwt_issuer") 
        return False
        
    if not hasattr(settings, 'app_jwt_audience') or not settings.app_jwt_audience:
        print("❌ 错误：未配置 app_jwt_audience")
        return False
    
    # 生成token
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=300)  # 5分钟有效期
    
    claims = {
        "iss": settings.app_jwt_issuer,
        "aud": settings.app_jwt_audience, 
        "sub": "backend-service",
        "scope": ["backend:admin"],
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": f"svc_{int(now.timestamp())}",
    }
    
    token = jwt.encode(claims, settings.app_jwt_secret, algorithm="HS256")
    print(f"✅ 成功生成JWT token (长度: {len(token)})")
    
    # 2. 验证JWT token
    print("\n2. 验证服务JWT token...")
    
    verification_result = await verify_service_jwt_token(token)
    
    if not verification_result.is_valid:
        print(f"❌ JWT验证失败: {verification_result.error_code} - {verification_result.error_message}")
        return False
    
    print("✅ JWT token验证成功")
    
    # 3. 检查服务上下文
    print("\n3. 检查服务上下文...")
    service_ctx = verification_result.service_context
    
    print(f"  - Subject: {service_ctx.sub}")
    print(f"  - Issuer: {service_ctx.iss}")
    print(f"  - Audience: {service_ctx.aud}")
    print(f"  - Scopes: {service_ctx.scopes}")
    print(f"  - Is Admin: {service_ctx.is_admin()}")
    print(f"  - Token Source: {service_ctx.token_source}")
    
    # 4. 测试权限检查
    print("\n4. 测试权限检查...")
    
    if service_ctx.has_scope("backend:admin"):
        print("✅ 具有 backend:admin 权限")
    else:
        print("❌ 缺少 backend:admin 权限")
        return False
    
    if service_ctx.is_admin():
        print("✅ 具有管理员权限")
    else:
        print("❌ 缺少管理员权限")
        return False
    
    # 5. 测试无效token
    print("\n5. 测试无效token处理...")
    
    invalid_result = await verify_service_jwt_token("invalid_token")
    if invalid_result.is_valid:
        print("❌ 无效token应该验证失败")
        return False
    else:
        print(f"✅ 无效token正确拒绝: {invalid_result.error_code}")
    
    print("\n=== 所有测试通过！ ===")
    return True


def check_settings():
    """检查必需的设置"""
    print("检查配置设置...")
    
    required_settings = [
        'app_jwt_secret',
        'app_jwt_issuer', 
        'app_jwt_audience'
    ]
    
    for setting in required_settings:
        if not hasattr(settings, setting) or not getattr(settings, setting):
            print(f"❌ 缺少配置: {setting}")
            return False
        else:
            print(f"✅ {setting}: 已配置")
    
    return True


if __name__ == "__main__":
    print("服务JWT认证集成测试")
    print("=" * 40)
    
    # 检查配置
    if not check_settings():
        print("\n❌ 配置检查失败，请检查.env文件")
        sys.exit(1)
    
    # 运行测试
    try:
        result = asyncio.run(test_service_jwt_flow())
        if result:
            print("\n🎉 所有测试成功通过！")
            sys.exit(0)
        else:
            print("\n❌ 测试失败")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)