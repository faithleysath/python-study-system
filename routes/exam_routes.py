import random
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from config import config
from db import (
    get_exam_detail, get_ongoing_exam, get_correct_questions_last_week,
    create_exam, get_exam_questions, update_exam_answer, get_student_exams,
    get_user_full_info
)
from questions import check_answer, get_question_by_id
from auth import auth_required

router = APIRouter(prefix="/api/exam")

@router.get("/config")
@auth_required()
async def get_exam_config(request: Request):
    """获取考试配置"""
    return {
        "examDuration": config.exam_duration,
        "questionCount": config.exam_question_count,
        "practiceThreshold": config.practice_threshold,
        "passScore": config.pass_score,
        "questionRangeDays": config.question_range_days,
        "enableExam": config.enable_exam
    }

@router.get("/check")
@auth_required()
async def check_exam(request: Request):
    """检查是否有进行中的考试"""
    student_id = request.cookies.get("studentId")
    return get_ongoing_exam(student_id)

@router.post("/start")
@auth_required()
async def start_exam(request: Request):
    """开始新考试"""
    # 检查考试功能是否开启
    if not config.enable_exam:
        raise HTTPException(status_code=403, detail="考试功能当前已关闭")
        
    student_id = request.cookies.get("studentId")
    
    # 检查学生个人考试权限
    user_info = get_user_full_info(student_id)
    if not user_info or not user_info.get("enable_exam", True):
        raise HTTPException(status_code=403, detail="您的考试权限已被禁用")
    
    # 获取一周内做对的不重复题目列表
    correct_questions = get_correct_questions_last_week(student_id)
    
    if len(correct_questions) < config.practice_threshold:
        raise HTTPException(status_code=400, detail=f"{config.question_range_days}天内做对的题目数量不足{config.practice_threshold}道")
    
    # 随机选择10道题目
    selected_questions = random.sample(correct_questions, config.exam_question_count)
    
    # 创建新考试
    return create_exam(student_id, selected_questions)

@router.get("/{exam_id}/questions")
@auth_required()
async def get_exam_questions_route(request: Request, exam_id: str):
    """获取考试题目"""
    student_id = request.cookies.get("studentId")
    result = get_exam_questions(exam_id, student_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="考试不存在或已结束")
    
    return result

@router.get("/history")
@auth_required()
async def get_exam_history(request: Request):
    """获取学生的历史考试记录"""
    student_id = request.cookies.get("studentId")
    return get_student_exams(student_id)

@router.get("/{exam_id}/detail")
@auth_required()
async def get_exam_detail_route(request: Request, exam_id: str):
    """获取考试的详细信息,包括题目内容、答案和解析"""
    student_id = request.cookies.get("studentId")
    result = get_exam_detail(exam_id, student_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="考试不存在")
    
    return result

@router.post("/{exam_id}/submit/{question_id}")
@auth_required()
async def submit_exam_answer(request: Request, exam_id: str, question_id: str, answer: dict = None):
    """提交考试答案"""
    student_id = request.cookies.get("studentId")
    
    # 获取考试信息
    ongoing_exam = get_ongoing_exam(student_id)
    if not ongoing_exam or not ongoing_exam['has_ongoing_exam'] or ongoing_exam['exam_id'] != exam_id:
        raise HTTPException(status_code=404, detail="考试不存在")
    
    # 获取考试题目信息
    exam_info = get_exam_questions(exam_id, student_id)
    if not exam_info:
        raise HTTPException(status_code=404, detail="考试不存在或已结束")
        
    # 检查考试时间
    current_time = datetime.now()
    end_time = datetime.fromisoformat(exam_info['end_time'])
    if current_time > end_time:
        raise HTTPException(status_code=400, detail="考试已超时")
        
    # 检查答案
    is_correct, explanation = check_answer(question_id, answer['answer'])
    
    # 更新考试记录
    result = update_exam_answer(exam_id, student_id, question_id, is_correct, answer['answer'])
    if not result:
        raise HTTPException(status_code=404, detail="考试不存在或已结束")
    
    # 返回详细结果
    return {
        "is_correct": is_correct,
        "explanation": explanation,
        "current_progress": result["current_progress"],
        "exam_status": result["exam_status"]
    }

@router.get("/question/{id}")
@auth_required()
async def get_question_by_id_route(request: Request, id: str):
    """获取指定ID的题目"""
    try:
        question = get_question_by_id(id)
        return {"question": question}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
