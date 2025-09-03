from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from db import get_user_stats, get_user_info, create_or_update_user
from models import LoginRequest
from utils import get_client_ip
from auth import verify_user_ip, auth_required
from config import config

router = APIRouter(prefix="/api")

@router.get("/user/check/{student_id}")
async def check_user(student_id: str):
    """检查用户是否存在"""
    if not student_id:
        raise HTTPException(status_code=400, detail="未提供学号")
    
    name = get_user_info(student_id)
    return {"exists": bool(name), "name": name if name else None}

@router.post("/auth/logout")
async def logout():
    """用户登出"""
    response = JSONResponse(content={"success": True, "message": "登出成功"})
    response.delete_cookie(key="studentId", path="/")
    return response

@router.get("/user/stats")
@auth_required()
async def get_stats(request: Request):
    """获取用户统计信息"""
    student_id = request.cookies.get("studentId")
    try:
        return get_user_stats(student_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/info")
@auth_required()
async def get_info(request: Request):
    """获取用户信息"""
    student_id = request.cookies.get("studentId")
    name = get_user_info(student_id)
    if not name:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return {"student_id": student_id, "name": name}

@router.post("/auth/login")
async def login(request: Request, login_data: LoginRequest):
    """用户登录"""
    if not login_data.student_id:
        raise HTTPException(status_code=400, detail="未提供学号")
        
    # 检查是否是新用户
    name = get_user_info(login_data.student_id)
    if not name:
        if not config.enable_registration:
            raise HTTPException(status_code=403, detail="系统当前不允许新用户注册")
        if not login_data.name:
            return {"success": False, "message": "需要输入姓名"}
    
    # 验证IP(如果是老用户)
    if name:
        valid, error_msg = await verify_user_ip(login_data.student_id, request)
        if not valid:
            raise HTTPException(status_code=403, detail=error_msg)
    
    # 创建或更新用户
    try:
        create_or_update_user(
            login_data.student_id,
            login_data.name or name,
            get_client_ip(request),
            default_ai_permission=config.default_ai_permission,
            default_exam_permission=config.default_exam_permission
        )
        response = {"success": True, "message": "登录成功"}
        # 创建响应对象
        response = JSONResponse(content=response)
        # 设置cookie,浏览器关闭时过期
        response.set_cookie(
            key="studentId",
            value=login_data.student_id,
            httponly=True,
            samesite="strict",
            secure=False  # 本地开发环境设为False
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
