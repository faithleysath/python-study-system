from datetime import datetime, timedelta
from functools import wraps
from typing import Tuple

from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
import passlib.handlers.bcrypt  # 显式导入，确保 PyInstaller 可以检测到


from config import config
from db import create_or_update_user, get_user_info, get_user_ip_info
from utils import get_client_ip

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT相关配置
SECRET_KEY = config.secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = config.token_expire_minutes

async def verify_user_ip(student_id: str, request: Request) -> Tuple[bool, str]:
    """验证用户IP地址
    
    Returns:
        tuple: (验证是否通过, 错误信息)
    """
    current_ip = get_client_ip(request)
    bound_ip, bound_time = get_user_ip_info(student_id)
    
    # 如果没有绑定IP或者不是今天绑定的,更新IP      
    today = datetime.now().date()
    bound_date = bound_time.date() if bound_time else None
    
    # 如果是已存在的用户
    name = get_user_info(student_id)
    if name:
        if not bound_date or bound_date != today or not bound_ip:
            create_or_update_user(student_id, name, current_ip)
            return True, ""
        return bound_ip == current_ip, f"异地登陆已被禁止!请明日再试,或联系系统管理员!"
    
    # 如果是新用户,允许访问登录页面
    return True, ""

def auth_required(is_page_route=False):
    """用户认证装饰器
    
    Args:
        is_page_route: 是否是页面路由。如果是页面路由,未登录时重定向到登录页面而不是返回错误。
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            student_id = request.cookies.get("studentId")
            
            # 未登录处理
            if not student_id:
                if is_page_route:
                    return RedirectResponse(url="/login")
                raise HTTPException(status_code=401, detail="未登录,请重新登录")
            
            if not get_user_info(student_id):
                if is_page_route:
                    return RedirectResponse(url="/login")
                raise HTTPException(status_code=401, detail="未登录,请重新登录")
            
            # IP验证失败处理
            valid, error_msg = await verify_user_ip(student_id, request)
            if not valid:
                if is_page_route:
                    response = RedirectResponse(url="/login")
                    response.delete_cookie(key="studentId", path="/")
                    return response
                raise HTTPException(status_code=403, detail=error_msg)
                
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# 管理员认证相关函数
def verify_admin_credentials(username: str, password: str) -> bool:
    """验证管理员凭据"""
    return (username == config.admin_username and 
            password == config.admin_password)

def create_access_token(data: dict) -> str:
    """创建JWT token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    """验证JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username != config.admin_username:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
        )

def verify_admin_token(token: str) -> bool:
    """验证管理员token"""
    try:
        verify_token(token)
        return True
    except HTTPException:
        return False

def admin_required():
    """管理员认证装饰器"""
    security = HTTPBearer()
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            credentials: HTTPAuthorizationCredentials = await security(request)
            verify_token(credentials.credentials)
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

async def get_current_user(request: Request):
    """获取当前登录用户"""
    student_id = request.cookies.get("studentId")
    
    # 未登录
    if not student_id:
        return None
    
    # 用户不存在
    name = get_user_info(student_id)
    if not name:
        return None
    
    # IP验证失败
    valid, _ = await verify_user_ip(student_id, request)
    if not valid:
        return None
    
    # 返回用户信息
    return type('User', (), {
        'student_id': student_id,
        'name': name
    })()
