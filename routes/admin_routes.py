import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import case, func, and_, true

from db import get_db, get_base_path, update_user_ai_permission, update_user_exam_permission_no_async
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

class UpdateExamPermissionRequest(BaseModel):
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

@api_router.post("/users/{student_id}/exam-permission")
@admin_required()
async def update_user_exam_permission_route(request: Request, student_id: str, permission: UpdateExamPermissionRequest):
    """更新用户的考试权限"""
    result = update_user_exam_permission_no_async(student_id, permission.enable)
    if not result:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"success": True}

@api_router.get("/users/progress")
@admin_required()
async def get_users_progress(request: Request):
    """获取所有用户的进度信息,按IP绑定时间排序"""
    with get_db() as db:
        today = datetime.now().date()

        # 1. 子查询: 计算每个学生的练习统计
        practice_stats_sub = (
            db.query(
                Record.student_id,
                func.count(Record.id).label("total_questions"),
                func.sum(case((Record.is_correct == true(), 1), else_=0)).label("correct_questions")
            )
            .group_by(Record.student_id)
            .subquery()
        )

        # 2. 子查询: 计算每个学生的考试统计
        exam_stats_sub = (
            db.query(
                Exam.student_id,
                func.count(Exam.id).label("exam_count")
            )
            .filter(Exam.status == "已完成")
            .group_by(Exam.student_id)
            .subquery()
        )

        # 3. 子查询: 获取每个学生的最新一次考试成绩
        latest_exam_sub = (
            db.query(
                Exam.student_id,
                (Exam.correct_count * 100.0 / Exam.question_count).label("last_exam_score"),
                func.row_number().over(
                    partition_by=Exam.student_id,
                    order_by=Exam.submit_time.desc()
                ).label("rn")
            )
            .filter(Exam.status == "已完成", Exam.question_count > 0)
            .subquery()
        )
        latest_exam_score_sub = (
            db.query(latest_exam_sub.c.student_id, latest_exam_sub.c.last_exam_score)
            .filter(latest_exam_sub.c.rn == 1)
            .subquery()
        )

        # 4. 子查询: 检查今天是否获得认证码
        code_today_sub = (
            db.query(CodeRecord.student_id)
            .filter(func.date(CodeRecord.get_time) == today)
            .distinct()
            .subquery()
        )

        # 5. 子查询: 计算今天的AI聊天统计
        chat_stats_sub = (
            db.query(
                AIChatRecord.student_id,
                func.count(AIChatRecord.id).label("chat_count"),
                func.sum(case((AIChatRecord.is_irrelevant == true(), 1), else_=0)).label("today_irrelevant_chats")
            )
            .filter(func.date(AIChatRecord.chat_time) == today)
            .group_by(AIChatRecord.student_id)
            .subquery()
        )

        # 主查询: 联合所有子查询
        query_result = (
            db.query(
                User,
                practice_stats_sub.c.total_questions,
                practice_stats_sub.c.correct_questions,
                exam_stats_sub.c.exam_count,
                latest_exam_score_sub.c.last_exam_score,
                code_today_sub.c.student_id.isnot(None).label("has_code"),
                chat_stats_sub.c.chat_count,
                chat_stats_sub.c.today_irrelevant_chats
            )
            .outerjoin(practice_stats_sub, User.student_id == practice_stats_sub.c.student_id)
            .outerjoin(exam_stats_sub, User.student_id == exam_stats_sub.c.student_id)
            .outerjoin(latest_exam_score_sub, User.student_id == latest_exam_score_sub.c.student_id)
            .outerjoin(code_today_sub, User.student_id == code_today_sub.c.student_id)
            .outerjoin(chat_stats_sub, User.student_id == chat_stats_sub.c.student_id)
            .order_by(User.bound_time.desc())
            .all()
        )

        progress_list = []
        for row in query_result:
            user, total_questions, correct_questions, exam_count, last_exam_score, has_code, chat_count, today_irrelevant_chats = row
            
            total_questions = total_questions or 0
            correct_questions = correct_questions or 0
            accuracy = (correct_questions / total_questions * 100) if total_questions > 0 else 0

            progress_list.append(UserProgress(
                student_id=user.student_id,
                name=user.name,
                bound_ip=user.bound_ip,
                bound_time=user.bound_time,
                total_questions=total_questions,
                correct_questions=correct_questions,
                accuracy=accuracy,
                exam_count=exam_count or 0,
                last_exam_score=round(last_exam_score, 2) if last_exam_score is not None else None,
                has_code=has_code,
                chat_count=chat_count or 0,
                today_irrelevant_chats=today_irrelevant_chats or 0,
                enable_ai=user.enable_ai
            ))
            
        return progress_list

@api_router.get("/stats/overview")
@admin_required()
async def get_system_overview(request: Request):
    """获取系统概览统计信息"""
    with get_db() as db:
        today = datetime.now().date()

        # 使用一个查询和多个子查询来获取所有统计数据
        
        # 用户统计
        user_stats = db.query(
            func.count(User.student_id).label("total_users"),
            func.count(case((func.date(User.bound_time) == today, User.student_id))).label("active_users")
        ).one()

        # 练习统计
        record_stats = db.query(
            func.count(Record.id).label("total_answers"),
            func.count(case((func.date(Record.answer_time) == today, Record.id))).label("today_answers"),
            func.sum(case((Record.is_correct == true(), 1), else_=0)).label("total_correct"),
            func.sum(case((and_(Record.is_correct == true(), func.date(Record.answer_time) == today), 1), else_=0)).label("today_correct")
        ).one()

        # 考试统计
        exam_stats = db.query(
            func.count(Exam.id).label("total_exams"),
            func.count(case((func.date(Exam.submit_time) == today, Exam.id))).label("today_exams"),
            func.avg(case((Exam.question_count > 0, Exam.correct_count * 100.0 / Exam.question_count))).label("avg_score"),
            func.avg(case((and_(Exam.question_count > 0, func.date(Exam.submit_time) == today), Exam.correct_count * 100.0 / Exam.question_count))).label("today_avg_score")
        ).filter(Exam.status == "已完成").one()

        # 认证统计
        code_stats = db.query(
            func.count(CodeRecord.id).label("total_codes"),
            func.count(func.distinct(case((func.date(CodeRecord.get_time) == today, CodeRecord.student_id)))).label("today_code_users")
        ).one()

        # 问答统计
        chat_stats = db.query(
            func.count(AIChatRecord.id).label("total_chats"),
            func.count(case((func.date(AIChatRecord.chat_time) == today, AIChatRecord.id))).label("today_chats"),
            func.sum(case((AIChatRecord.is_irrelevant == true(), 1), else_=0)).label("irrelevant_chats"),
            func.sum(case((and_(AIChatRecord.is_irrelevant == true(), func.date(AIChatRecord.chat_time) == today), 1), else_=0)).label("today_irrelevant_chats")
        ).one()

        # 剩余认证码数量
        codes_file = os.path.join(get_base_path(), 'data', 'codes.txt')
        try:
            with open(codes_file, "r") as f:
                remaining_codes = len([line for line in f if line.strip()])
        except FileNotFoundError:
            remaining_codes = 0

        total_answers = record_stats.total_answers or 0
        today_answers = record_stats.today_answers or 0
        total_correct = record_stats.total_correct or 0
        today_correct = record_stats.today_correct or 0

        return {
            # 用户统计
            "total_users": user_stats.total_users or 0,
            "active_users": user_stats.active_users or 0,
            
            # 练习统计
            "total_answers": total_answers,
            "today_answers": today_answers,
            "accuracy": (total_correct / total_answers * 100) if total_answers > 0 else 0,
            "today_accuracy": (today_correct / today_answers * 100) if today_answers > 0 else 0,
            
            # 考试统计
            "total_exams": exam_stats.total_exams or 0,
            "today_exams": exam_stats.today_exams or 0,
            "avg_score": round(exam_stats.avg_score, 2) if exam_stats.avg_score else 0,
            "today_avg_score": round(exam_stats.today_avg_score, 2) if exam_stats.today_avg_score else 0,
            
            # 认证统计
            "total_codes": code_stats.total_codes or 0,
            "today_code_users": code_stats.today_code_users or 0,
            "remaining_codes": remaining_codes,
            
            # 问答统计
            "total_chats": chat_stats.total_chats or 0,
            "today_chats": chat_stats.today_chats or 0,
            "irrelevant_chats": chat_stats.irrelevant_chats or 0,
            "today_irrelevant_chats": chat_stats.today_irrelevant_chats or 0
        }

@api_router.get("/chat/{student_id}")
@admin_required()
async def get_chat_records(request: Request, student_id: str):
    """获取指定学生的问答记录"""
    with get_db() as db:
        user = db.query(User).filter(User.student_id == student_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # 联合查询获取统计信息和聊天记录
        result = db.query(
            User.student_id,
            User.name,
            func.count(AIChatRecord.id).label("total_chats"),
            func.sum(case((AIChatRecord.is_irrelevant == True, 1), else_=0)).label("irrelevant_chats")
        ).filter(
            User.student_id == student_id
        ).join(
            AIChatRecord, User.student_id == AIChatRecord.student_id
        ).group_by(
            User.student_id
        ).first()
        
        # 单独获取聊天记录列表
        chats = db.query(AIChatRecord).filter(
            AIChatRecord.student_id == student_id
        ).order_by(AIChatRecord.chat_time.desc()).all()
        
        return {
            "student_id": user.student_id,
            "student_name": user.name,
            "total_chats": result.total_chats if result else 0,
            "irrelevant_chats": result.irrelevant_chats if result else 0,
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
        today = datetime.now().date()

        # 联合查询获取用户信息、练习统计和今日认证码信息
        result = db.query(
            User.student_id,
            User.name,
            User.bound_ip,
            User.bound_time,
            User.enable_ai,
            func.count(Record.id).label('total_questions'),
            func.sum(case((Record.is_correct == True, 1), else_=0)).label('correct_questions'),
            CodeRecord.get_time.label('code_time')
        ).filter(
            User.student_id == student_id
        ).outerjoin(
            Record, User.student_id == Record.student_id
        ).outerjoin(
            CodeRecord, and_(
                User.student_id == CodeRecord.student_id,
                func.date(CodeRecord.get_time) == today
            )
        ).group_by(
            User.student_id
        ).first()
        
        if not result:
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
            "score": round(exam.correct_count / exam.question_count * 100, 1),
            "question_count": exam.question_count,
            "correct_count": exam.correct_count
        } for exam in exams]
        
        total_questions = result.total_questions or 0
        correct_questions = result.correct_questions or 0
        
        return {
            "user_info": {
                "student_id": result.student_id,
                "name": result.name,
                "bound_ip": result.bound_ip,
                "bound_time": result.bound_time,
                "has_code": result.code_time is not None,
                "code_time": result.code_time,
                "enable_ai": result.enable_ai
            },
            "practice_stats": {
                "total_questions": total_questions,
                "correct_questions": correct_questions,
                "accuracy": (correct_questions / total_questions * 100) 
                           if total_questions else 0
            },
            "exam_records": exam_records
        }
