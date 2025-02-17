from fastapi import Request
from fastapi.responses import RedirectResponse

from db import get_ongoing_exam, get_ip_bound_user
from utils import get_client_ip

async def exam_check_middleware(request: Request, call_next):
    """检查IP是否有进行中的考试的中间件"""
    
    # 获取客户端IP
    client_ip = get_client_ip(request)
    
    # 允许访问的路径
    allowed_paths = {
        "/login",  # 登录页面
        "/static",  # 静态资源
        "/exam",  # 考试页面
        "/api/exam",  # 考试相关API
        "/api/user",  # 用户相关API
        "/api/auth"  # 认证相关API
    }
    
    # 检查是否是允许的路径
    path = request.url.path
    if any(path.startswith(allowed) for allowed in allowed_paths):
        return await call_next(request)
    
    # 获取该IP绑定的所有用户
    student_ids = get_ip_bound_user(client_ip)
    for student_id in student_ids:
        # 检查每个用户是否有进行中的考试
        exam_status = get_ongoing_exam(student_id)
        if exam_status.get("has_ongoing_exam"):
            # 只要有一个用户有进行中的考试,就重定向到考试页面
            return RedirectResponse(url="/exam")
    
    # 如果没有进行中的考试,继续处理请求
    return await call_next(request)
