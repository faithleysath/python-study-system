import os

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from db import get_db, get_admin_exam_detail
from models import User, AIChatRecord
from auth import auth_required, admin_required
from config import config

from paths import get_template_path

router = APIRouter()

# 设置模板目录
templates = Jinja2Templates(directory=get_template_path())

@router.get("/", response_class=HTMLResponse)
@router.get("/index.html", response_class=HTMLResponse)
@auth_required(is_page_route=True)
async def read_root(request: Request):
    """返回首页"""
    return templates.TemplateResponse("index.html", {"request": request, "version": config.version, "detail_info": config.detail_info})

@router.get("/login.html")
@router.get("/login")
async def read_login():
    """返回登录页"""
    return FileResponse(os.path.join(get_template_path(), "login.html"))

@router.get("/practice.html", response_class=HTMLResponse)
@router.get("/practice", response_class=HTMLResponse)
@auth_required(is_page_route=True)
async def read_practice(request: Request):
    """返回练习页"""
    return templates.TemplateResponse("practice.html", {"request": request, "version": config.version, "detail_info": config.detail_info})

@router.get("/exam.html", response_class=HTMLResponse)
@router.get("/exam", response_class=HTMLResponse)
@auth_required(is_page_route=True)
async def read_exam(request: Request):
    """返回考试页"""
    return templates.TemplateResponse("exam.html", {"request": request, "version": config.version, "detail_info": config.detail_info})

@router.get("/exam/history.html", response_class=HTMLResponse)
@router.get("/exam/history", response_class=HTMLResponse)
@auth_required(is_page_route=True)
async def read_exam_history(request: Request):
    """返回历史考试页"""
    return templates.TemplateResponse("exam_history.html", {"request": request, "version": config.version, "detail_info": config.detail_info})

@router.get("/chat.html")
@router.get("/chat")
@auth_required(is_page_route=True)
async def read_chat(request: Request):
    """返回AI问答页"""
    return FileResponse(os.path.join(get_template_path(), "chat.html"))

@router.get("/admin/")
@router.get("/admin/login.html")
@router.get("/admin/login")
async def read_admin_login():
    """返回管理员登录页"""
    return FileResponse(os.path.join(get_template_path(), "admin_login.html"))

@router.get("/admin/dashboard.html")
@router.get("/admin/dashboard")
async def read_admin_dashboard():
    """返回管理员仪表板页"""
    return FileResponse(os.path.join(get_template_path(), "admin_dashboard.html"))

@router.get("/admin/chat/{student_id}", response_class=HTMLResponse)
@admin_required()
async def read_admin_chat_detail(request: Request, student_id: str):
    """返回管理员查看的学生问答记录页面"""
    with get_db() as db:
        user = db.query(User).filter(User.student_id == student_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # 获取该学生的所有问答记录
        chats = db.query(AIChatRecord).filter(
            AIChatRecord.student_id == student_id
        ).order_by(AIChatRecord.chat_time.desc()).all()
        
        # 统计总数和无关问题数
        total_chats = len(chats)
        irrelevant_chats = sum(1 for chat in chats if chat.is_irrelevant)
        
        return templates.TemplateResponse("admin_chat_detail.html", {
            "request": request,
            "student_id": user.student_id,
            "student_name": user.name,
            "total_chats": total_chats,
            "irrelevant_chats": irrelevant_chats,
            "chats": [{
                "id": chat.id,
                "question": chat.question,
                "answer": chat.answer,
                "chat_time": chat.chat_time.strftime("%Y-%m-%d %H:%M:%S"),
                "is_irrelevant": chat.is_irrelevant
            } for chat in chats]
        })

@router.get("/admin/exam/{exam_id}", response_class=HTMLResponse)
@admin_required()
async def read_admin_exam_detail(request: Request, exam_id: str):
    """返回管理员查看的考试详情页"""
    # 获取考试详情
    exam_detail = get_admin_exam_detail(exam_id)
    if not exam_detail:
        raise HTTPException(status_code=404, detail="考试或学生不存在")
    
    # 准备模板上下文
    context = {
        "request": request,  # FastAPI的Jinja2Templates需要request参数
        "chr": chr,  # 添加chr函数到模板上下文
        **exam_detail,
        "start_time": exam_detail["start_time"].strftime("%Y-%m-%d %H:%M:%S")  # 格式化时间
    }
    
    return templates.TemplateResponse(
        "admin_exam_detail.html",
        context
    )
