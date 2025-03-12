import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import case, func, and_, true

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
        today = datetime.now().date()

        # 子查询: 获取每个用户的最新考试ID和成绩
        latest_exam_subquery = (
            db.query(
                Exam.student_id,
                Exam.correct_count,
                Exam.question_count,
                func.row_number().over(
                    partition_by=Exam.student_id,
                    order_by=Exam.submit_time.desc()
                ).label("row_num")
            )
            .filter(Exam.status == "已完成")
            .subquery()
        )
        
        # 只保留每个用户的最新考试记录
        latest_exam = (
            db.query(
                latest_exam_subquery.c.student_id,
                latest_exam_subquery.c.correct_count,
                latest_exam_subquery.c.question_count
            )
            .filter(latest_exam_subquery.c.row_num == 1)
            .subquery()
        )
        
        # 使用联合查询获取所有所需数据，减少数据库往返次数
        query_result = (
            db.query(
                User.student_id,
                User.name,
                User.bound_ip,
                User.bound_time,
                User.enable_ai,
                # 答题总数
                func.count(Record.id).label("total_questions"),
                # 答对题数
                func.sum(case((Record.is_correct == True, 1), else_=0)).label("correct_questions"),
                # 考试数量
                func.count(func.distinct(case((Exam.status == "已完成", Exam.exam_id)))).label("exam_count"),
                # 最新考试成绩
                latest_exam.c.correct_count,
                latest_exam.c.question_count,
                # 今日有无认证码
                func.count(func.distinct(case(
                    (func.date(CodeRecord.get_time) == today, CodeRecord.id)
                ))).label("has_code_today"),
                # 今日提问数量
                func.count(func.distinct(case(
                    (func.date(AIChatRecord.chat_time) == today, AIChatRecord.id)
                ))).label("chat_count"),
                # 今日无关问题数
                func.count(func.distinct(case(
                    (and_(
                        func.date(AIChatRecord.chat_time) == today,
                        AIChatRecord.is_irrelevant == True
                    ), AIChatRecord.id)
                ))).label("today_irrelevant_chats"),
            )
            .outerjoin(Record, User.student_id == Record.student_id)
            .outerjoin(Exam, User.student_id == Exam.student_id)
            .outerjoin(CodeRecord, User.student_id == CodeRecord.student_id)
            .outerjoin(AIChatRecord, User.student_id == AIChatRecord.student_id)
            .outerjoin(latest_exam, User.student_id == latest_exam.c.student_id)
            .group_by(User.student_id)
            .order_by(User.bound_time.desc())
            .all()
        )
        
        progress_list = []
        for result in query_result:
            # 计算正确率
            total_questions = result.total_questions or 0
            correct_questions = result.correct_questions or 0
            accuracy = (correct_questions / total_questions * 100) if total_questions > 0 else 0
            
            # 计算最新考试成绩
            last_exam_score = None
            if result.correct_count is not None and result.question_count is not None:
                last_exam_score = round(result.correct_count / result.question_count * 100, 2)
            
            progress_list.append(UserProgress(
                student_id=result.student_id,
                name=result.name,
                bound_ip=result.bound_ip,
                bound_time=result.bound_time,
                total_questions=total_questions,
                correct_questions=correct_questions,
                accuracy=accuracy,
                exam_count=result.exam_count or 0,
                last_exam_score=last_exam_score,
                has_code=result.has_code_today > 0,
                chat_count=result.chat_count or 0,
                today_irrelevant_chats=result.today_irrelevant_chats or 0,
                enable_ai=result.enable_ai
            ))
        
        return progress_list

@api_router.get("/stats/overview")
@admin_required()
async def get_system_overview(request: Request):
    """获取系统概览统计信息"""
    with get_db() as db:
        today = datetime.now().date()
        
        # 使用单个查询获取大部分统计数据
        stats = db.query(
            # 用户统计
            func.count(func.distinct(User.student_id)).label("total_users"),
            func.count(func.distinct(case(
                (func.date(User.bound_time) == today, User.student_id)
            ))).label("active_users"),
            
            # 练习统计
            func.count(Record.id).label("total_answers"),
            func.count(case(
                (func.date(Record.answer_time) == today, Record.id)
            )).label("today_answers"),
            
            func.count(case(
                (Record.is_correct == True, Record.id)
            )).label("total_correct"),
            func.count(case(
                (and_(Record.is_correct == True, func.date(Record.answer_time) == today), Record.id)
            )).label("today_correct"),
            
            # 考试统计
            func.count(case(
                (Exam.status == "已完成", Exam.exam_id)
            )).label("total_exams"),
            func.count(case(
                (and_(Exam.status == "已完成", func.date(Exam.submit_time) == today), Exam.exam_id)
            )).label("today_exams"),
            
            # 问答统计
            func.count(AIChatRecord.id).label("total_chats"),
            func.count(case(
                (func.date(AIChatRecord.chat_time) == today, AIChatRecord.id)
            )).label("today_chats"),
            
            func.count(case(
                (AIChatRecord.is_irrelevant == True, AIChatRecord.id)
            )).label("irrelevant_chats"),
            func.count(case(
                (and_(AIChatRecord.is_irrelevant == True, func.date(AIChatRecord.chat_time) == today), AIChatRecord.id)
            )).label("today_irrelevant_chats"),
            
            # 认证统计
            func.count(CodeRecord.id).label("total_codes"),
            func.count(func.distinct(case(
                (func.date(CodeRecord.get_time) == today, CodeRecord.student_id)
            ))).label("today_code_users"),
        ).outerjoin(
            Record, true()
        ).outerjoin(
            Exam, true()
        ).outerjoin(
            AIChatRecord, true()
        ).outerjoin(
            CodeRecord, true()
        ).first()
        
        # 单独查询平均分数，因为需要更复杂的计算
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
        
        # 剩余认证码数量
        codes_file = os.path.join(get_base_path(), 'data', 'codes.txt')
        with open(codes_file, "r") as f:
            remaining_codes = len(f.readlines())
        
        return {
            # 用户统计
            "total_users": stats.total_users or 0,
            "active_users": stats.active_users or 0,
            
            # 练习统计
            "total_answers": stats.total_answers or 0,
            "today_answers": stats.today_answers or 0,
            "accuracy": (stats.total_correct / stats.total_answers * 100) if stats.total_answers and stats.total_answers > 0 else 0,
            "today_accuracy": (stats.today_correct / stats.today_answers * 100) if stats.today_answers and stats.today_answers > 0 else 0,
            
            # 考试统计
            "total_exams": stats.total_exams or 0,
            "today_exams": stats.today_exams or 0,
            "avg_score": round(avg_score, 2) if avg_score else 0,
            "today_avg_score": round(today_avg_score, 2) if today_avg_score else 0,
            
            # 认证统计
            "total_codes": stats.total_codes or 0,
            "today_code_users": stats.today_code_users or 0,
            "remaining_codes": remaining_codes,
            
            # 问答统计
            "total_chats": stats.total_chats or 0,
            "today_chats": stats.today_chats or 0,
            "irrelevant_chats": stats.irrelevant_chats or 0,
            "today_irrelevant_chats": stats.today_irrelevant_chats or 0
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
