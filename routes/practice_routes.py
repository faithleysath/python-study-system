from fastapi import APIRouter, HTTPException, Request

from db import save_answer_record, get_excluded_questions, get_question_record
from models import AnswerRequest
from questions import get_random_question, check_answer, get_total_enabled_questions, get_question_by_id
from auth import auth_required

router = APIRouter(prefix="/api/practice")

@router.get("/question")
@auth_required()
async def get_question(request: Request):
    """获取随机题目"""
    student_id = request.cookies.get("studentId")
    try:
        question = get_random_question(student_id)
        return {"question": question}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
@auth_required()
async def get_stats(request: Request):
    """获取题库统计信息"""
    student_id = request.cookies.get("studentId")
    try:
        total_count = get_total_enabled_questions()
        excluded_count = len(get_excluded_questions(student_id))
        return {
            "total_count": total_count,
            "excluded_count": excluded_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

@router.get("/question/{question_id}/record")
@auth_required()
async def get_question_stats(request: Request, question_id: str):
    """获取题目答题记录"""
    student_id = request.cookies.get("studentId")
    try:
        record = get_question_record(student_id, question_id)
        return {
            "correct_count": record["correct_count"],
            "wrong_count": record["wrong_count"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/answer")
@auth_required()
async def submit_answer(request: Request, answer_data: AnswerRequest):
    """提交答案"""
    student_id = request.cookies.get("studentId")
    
    try:
        # 检查答案
        is_correct, explanation = check_answer(answer_data.question_id, answer_data.answer)
        
        # 保存答题记录
        save_answer_record(student_id, answer_data.question_id, is_correct)
        
        return {
            "correct": is_correct,
            "explanation": explanation
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
