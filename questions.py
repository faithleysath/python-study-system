import json
import os
import random
from functools import lru_cache
from typing import Union, List, Tuple

from fastapi import HTTPException

from models import Question, QuestionResponse, QuestionType, Record, ExamRecord
from paths import get_base_path

# 初始化questions.json
def _init_questions_json():
    """初始化questions.json文件（如果不存在）"""
    questions_path = os.path.join(get_base_path(), 'data', 'questions.json')
    if not os.path.exists(questions_path):
        # 确保data目录存在
        os.makedirs(os.path.dirname(questions_path), exist_ok=True)
        # 创建空的题库结构
        with open(questions_path, 'w', encoding='utf-8') as f:
            json.dump({'questions': []}, f, ensure_ascii=False, indent=2)

# 在模块导入时初始化
_init_questions_json()

@lru_cache()
def load_questions() -> List[Question]:
    """加载题库"""
    try:
        questions_path = os.path.join(get_base_path(), 'data', 'questions.json')
        with open(questions_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [Question(**q) for q in data["questions"]]
    except FileNotFoundError:
        return []

def get_total_enabled_questions() -> int:
    """获取题库总启用题目数量"""
    questions = load_questions()
    enabled_questions = [q for q in questions if q.enabled]
    return len(enabled_questions)

def get_random_question(student_id: str) -> QuestionResponse:
    """获取随机题目"""
    # 加载题库
    questions = load_questions()
    if not questions:
        raise HTTPException(status_code=404, detail="题库为空")
    
    # 获取需要排除的题目ID
    from db import get_excluded_questions
    excluded_questions = get_excluded_questions(student_id)
    
    # 过滤可用题目
    available_questions = [
        q for q in questions
        if q.id not in excluded_questions and q.enabled
    ]
    
    if not available_questions:
        raise HTTPException(status_code=404, detail="没有可用的题目")
    
    # 随机选择一道题目
    question = random.choice(available_questions)
    
    # 处理返回的题目数据
    question_response = QuestionResponse(
        id=question.id,
        type=question.type,
        content=question.content,
        difficulty=question.difficulty
    )
    
    # 选择题需要包含选项
    if question.type in [QuestionType.SINGLE, QuestionType.MULTIPLE]:
        question_response.options = question.options
    
    return question_response

def get_question_by_id(question_id: str, include_answer: bool = False) -> Union[Question, QuestionResponse]:
    """获取指定ID的题目
    
    Args:
        question_id: 题目ID
        include_answer: 是否包含答案,用于考试结束后显示
    """
    questions = load_questions()
    question = next((q for q in questions if q.id == question_id), None)
    
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    
    if include_answer:
        return question
        
    question_response = QuestionResponse(
        id=question.id,
        type=question.type,
        content=question.content,
        difficulty=question.difficulty
    )
    
    if question.type in [QuestionType.SINGLE, QuestionType.MULTIPLE]:
        question_response.options = question.options
        
    return question_response

def check_answer(question_id: str, user_answer: Union[str, List[str], bool]) -> Tuple[bool, str]:
    """检查答案"""
    questions = load_questions()
    question = next((q for q in questions if q.id == question_id), None)
    
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    
    correct = False
    if question.type == QuestionType.SINGLE:
        correct = user_answer == question.answer
    elif question.type == QuestionType.MULTIPLE:
        user_answers = set(user_answer if isinstance(user_answer, list) else [user_answer])
        correct = user_answers == set(question.answer)
    elif question.type == QuestionType.JUDGE:
        correct = user_answer == question.answer
    elif question.type == QuestionType.BLANK:
        correct = user_answer.strip().lower() == question.answer.strip().lower()
    elif question.type == QuestionType.ESSAY:
        # 问答题暂时只要求包含关键词
        correct = all(keyword.lower() in user_answer.lower() for keyword in question.answer.split())
    
    return correct, question.explanation or ""

def update_question(question_id: str, question_data: dict) -> None:
    """更新题目或创建新题目
    
    Args:
        question_id: 题目ID
        question_data: 题目数据，包含content, type, difficulty, options, answer, explanation等字段
    """
    # 读取现有题目
    questions_path = os.path.join(get_base_path(), 'data', 'questions.json')
    with open(questions_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 更新题目或创建新题目
    for i, q in enumerate(data['questions']):
        if q['id'] == question_id:
            # 保持原有的其他字段不变
            original_data = q.copy()
            original_data.update(question_data)
            data['questions'][i] = original_data
            break
    else:
        # 如果题目不存在，则创建新题目
        new_question = {'id': question_id}
        new_question.update(question_data)
        data['questions'].append(new_question)
    
    # 保存更新
    with open(questions_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # 清除缓存
    load_questions.cache_clear()

def delete_question(question_id: str) -> None:
    """删除指定ID的题目及其相关记录
    
    Args:
        question_id: 题目ID
    """
    from db import get_db
    
    # 删除题目相关的记录
    with get_db() as db:
        # 删除普通答题记录
        db.query(Record).filter(Record.question_id == question_id).delete()
        # 删除考试记录
        db.query(ExamRecord).filter(ExamRecord.question_id == question_id).delete()
    
    # 读取现有题目
    questions_path = os.path.join(get_base_path(), 'data', 'questions.json')
    with open(questions_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 删除题目
    data['questions'] = [q for q in data['questions'] if q['id'] != question_id]
    
    # 保存更新
    with open(questions_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # 清除缓存
    load_questions.cache_clear()
