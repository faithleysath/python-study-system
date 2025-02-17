import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import case, func

from db import get_db, get_base_path, update_user_ai_permission
from models import User, Record, Exam, CodeRecord, AIChatRecord
from auth import verify_admin_credentials, create_access_token, admin_required

from paths import get_template_path

router = APIRouter()
templates = Jinja2Templates(directory=get_template_path())

api_router = APIRouter(prefix="/api/admin")

class AdminLoginRequest(BaseModel):
    username: str
    password: str

class UserProgress(BaseModel):
    student_id: str
    name: str
    bound_ip: str
    bound_time: datetime
    total_questions: int
    correct_questions: int
    accuracy: float
    exam_count: int
    last_exam_score: Optional[float] = None
    has_code: bool = False
    chat_count: int = 0
    today_irrelevant_chats: int = 0
    enable_ai: bool = True

class UpdateAIPermissionRequest(BaseModel):
    enable: bool

@api_router.post("/login")
async def admin_login(login_data: AdminLoginRequest):
    """管理员登录"""
    if not verify_admin_credentials(login_data.username, login_data.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token({"sub": login_data.username})
    return {"access_token": access_token, "token_type": "bearer"}

@api_router.post("/users/{student_id}/ai-permission")
@admin_required()
async def update_user_ai_permission_route(request: Request, student_id: str, permission: UpdateAIPermissionRequest):
    """更新用户的AI使用权限"""
    result = await update_user_ai_permission(student_id, permission.enable)
    if not result:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"success": True}

@api_router.get("/users/progress")
@admin_required()
async def get_users_progress(request: Request):
    """获取所有用户的进度信息,按IP绑定时间排序"""
    with get_db() as db:
        # 获取所有用户
        users = db.query(User).order_by(User.bound_time.desc()).all()
        
        progress_list = []
        for user in users:
            # 获取用户答题统计
            total_questions = db.query(Record).filter(
                Record.student_id == user.student_id
            ).count()
            
            correct_questions = db.query(Record).filter(
                Record.student_id == user.student_id,
                Record.is_correct == True
            ).count()
            
            # 计算正确率
            accuracy = (correct_questions / total_questions * 100) if total_questions > 0 else 0
            
            # 获取考试统计
            exam_count = db.query(Exam).filter(
                Exam.student_id == user.student_id,
                Exam.status == "已完成"
            ).count()
            
            # 获取最近一次考试成绩
            last_exam = db.query(Exam).filter(
                Exam.student_id == user.student_id,
                Exam.status == "已完成"
            ).order_by(Exam.submit_time.desc()).first()
            
            last_exam_score = None
            if last_exam:
                last_exam_score = round(last_exam.correct_count / last_exam.question_count * 100,2)
            
            # 检查用户是否在今天获得认证码
            today = datetime.now().date()
            has_code = db.query(CodeRecord).filter(
                CodeRecord.student_id == user.student_id,
                func.date(CodeRecord.get_time) == today
            ).first() is not None
            
            # 获取问答数量和今日无关问题数
            chat_count = db.query(AIChatRecord).filter(
                AIChatRecord.student_id == user.student_id,
                func.date(AIChatRecord.chat_time) == today
            ).count()
            
            # 获取今日无关问题数
            today_irrelevant_chats = db.query(AIChatRecord).filter(
                AIChatRecord.student_id == user.student_id,
                AIChatRecord.is_irrelevant == True,
                func.date(AIChatRecord.chat_time) == today
            ).count()
            
            progress_list.append(UserProgress(
                student_id=user.student_id,
                name=user.name,
                bound_ip=user.bound_ip,
                bound_time=user.bound_time,
                total_questions=total_questions,
                correct_questions=correct_questions,
                accuracy=accuracy,
                exam_count=exam_count,
                last_exam_score=last_exam_score,
                has_code=has_code,
                chat_count=chat_count,
                today_irrelevant_chats=today_irrelevant_chats,
                enable_ai=user.enable_ai
            ))
        
        return progress_list

@api_router.get("/stats/overview")
@admin_required()
async def get_system_overview(request: Request):
    """获取系统概览统计信息"""
    with get_db() as db:
        today = datetime.now().date()
        
        # 用户统计
        total_users = db.query(func.count(User.student_id)).scalar()
        active_users = db.query(func.count(func.distinct(User.student_id))).filter(
            func.date(User.bound_time) == today
        ).scalar()
        
        # 练习统计
        total_answers = db.query(func.count(Record.id)).scalar()
        today_answers = db.query(func.count(Record.id)).filter(
            func.date(Record.answer_time) == today
        ).scalar()
        
        total_correct = db.query(func.count(Record.id)).filter(
            Record.is_correct == True
        ).scalar()
        today_correct = db.query(func.count(Record.id)).filter(
            Record.is_correct == True,
            func.date(Record.answer_time) == today
        ).scalar()
        
        # 考试统计
        total_exams = db.query(func.count(Exam.exam_id)).filter(
            Exam.status == "已完成"
        ).scalar()
        today_exams = db.query(func.count(Exam.exam_id)).filter(
            Exam.status == "已完成",
            func.date(Exam.submit_time) == today
        ).scalar()
        
        avg_score = db.query(
            func.avg(Exam.correct_count * 100.0 / Exam.question_count)
        ).filter(
            Exam.status == "已完成"
        ).scalar()
        
        today_avg_score = db.query(
            func.avg(Exam.correct_count * 100.0 / Exam.question_count)
        ).filter(
            Exam.status == "已完成",
            func.date(Exam.submit_time) == today
        ).scalar()
        
        # 认证统计
        total_codes = db.query(func.count(CodeRecord.id)).scalar()
        today_code_users = db.query(func.count(func.distinct(CodeRecord.student_id))).filter(
            func.date(CodeRecord.get_time) == today
        ).scalar()
        
        # 剩余认证码数量
        codes_file = os.path.join(get_base_path(), 'data', 'codes.txt')
        with open(codes_file, "r") as f:
            remaining_codes = len(f.readlines())
        
        # 问答统计
        total_chats = db.query(func.count(AIChatRecord.id)).scalar()
        today_chats = db.query(func.count(AIChatRecord.id)).filter(
            func.date(AIChatRecord.chat_time) == today
        ).scalar()
        
        irrelevant_chats = db.query(func.count(AIChatRecord.id)).filter(
            AIChatRecord.is_irrelevant == True
        ).scalar()
        today_irrelevant_chats = db.query(func.count(AIChatRecord.id)).filter(
            AIChatRecord.is_irrelevant == True,
            func.date(AIChatRecord.chat_time) == today
        ).scalar()
        
        return {
            # 用户统计
            "total_users": total_users,
            "active_users": active_users,
            
            # 练习统计
            "total_answers": total_answers,
            "today_answers": today_answers,
            "accuracy": (total_correct / total_answers * 100) if total_answers > 0 else 0,
            "today_accuracy": (today_correct / today_answers * 100) if today_answers > 0 else 0,
            
            # 考试统计
            "total_exams": total_exams,
            "today_exams": today_exams,
            "avg_score": round(avg_score, 2) if avg_score else 0,
            "today_avg_score": round(today_avg_score, 2) if today_avg_score else 0,
            
            # 认证统计
            "total_codes": total_codes,
            "today_code_users": today_code_users,
            "remaining_codes": remaining_codes,
            
            # 问答统计
            "total_chats": total_chats,
            "today_chats": today_chats,
            "irrelevant_chats": irrelevant_chats,
            "today_irrelevant_chats": today_irrelevant_chats
        }

@api_router.get("/chat/{student_id}")
@admin_required()
async def get_chat_records(request: Request, student_id: str):
    """获取指定学生的问答记录"""
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
        
        return {
            "student_id": user.student_id,
            "student_name": user.name,
            "total_chats": total_chats,
            "irrelevant_chats": irrelevant_chats,
            "chats": [{
                "id": chat.id,
                "question": chat.question,
                "answer": chat.answer,
                "chat_time": chat.chat_time,
                "is_irrelevant": chat.is_irrelevant
            } for chat in chats]
        }

@api_router.post("/chat/{chat_id}/toggle-relevance")
@admin_required()
async def toggle_chat_relevance(request: Request, chat_id: int):
    """切换问题的相关性标记"""
    with get_db() as db:
        chat = db.query(AIChatRecord).filter(AIChatRecord.id == chat_id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat record not found")
        
        chat.is_irrelevant = not chat.is_irrelevant
        db.commit()
        return {"success": True}

@api_router.get("/users/{student_id}/detail")
@admin_required()
async def get_user_detail(request: Request, student_id: str):
    """获取指定用户的详细信息"""
    with get_db() as db:
        user = db.query(User).filter(User.student_id == student_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # 获取用户的考试记录
        exams = db.query(Exam).filter(
            Exam.student_id == student_id,
            Exam.status == "已完成"
        ).order_by(Exam.submit_time.desc()).all()
        
        exam_records = [{
            "exam_id": exam.exam_id,
            "start_time": exam.start_time,
            "submit_time": exam.submit_time,
            "score": round(exam.correct_count / exam.question_count * 100,1),
            "question_count": exam.question_count,
            "correct_count": exam.correct_count
        } for exam in exams]
        
        # 获取练习统计
        practice_stats = db.query(
            func.count(Record.id).label('total'),
            func.sum(case((Record.is_correct == True, 1), else_=0)).label('correct')
        ).filter(Record.student_id == student_id).first()
        
        # 获取今天的认证码信息
        today = datetime.now().date()
        code_record = db.query(CodeRecord).filter(
            CodeRecord.student_id == student_id,
            func.date(CodeRecord.get_time) == today
        ).first()
        
        return {
            "user_info": {
                "student_id": user.student_id,
                "name": user.name,
                "bound_ip": user.bound_ip,
                "bound_time": user.bound_time,
                "has_code": code_record is not None,
                "code_time": code_record.get_time if code_record else None,
                "enable_ai": user.enable_ai
            },
            "practice_stats": {
                "total_questions": practice_stats.total or 0,
                "correct_questions": practice_stats.correct or 0,
                "accuracy": (practice_stats.correct / practice_stats.total * 100) 
                           if practice_stats.total else 0
            },
            "exam_records": exam_records
        }
