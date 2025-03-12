from datetime import datetime
from enum import Enum
from typing import Optional, List, Union

from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base

__all__ = ['Base', 'User', 'Record', 'CodeRecord', 'QuestionType', 'Question', 'QuestionResponse', 'LoginRequest', 'AnswerRequest', 'Exam', 'ExamRecord', 'AIChatRecord']

Base = declarative_base()

# 数据库模型
class User(Base):
    __tablename__ = 'users'
    
    student_id = Column(String(20), primary_key=True)
    name = Column(String(50), nullable=False)
    bound_ip = Column(String(15))
    bound_time = Column(DateTime, index=True)
    enable_ai = Column(Boolean, default=True)  # 是否允许使用AI问答,默认允许

class Record(Base):
    __tablename__ = 'records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(20), ForeignKey('users.student_id'), index=True)
    question_id = Column(String(20))
    is_correct = Column(Boolean, index=True)
    student_answer = Column(String(500))  # 存储学生的答案,可能是字符串、列表或布尔值的JSON字符串
    answer_time = Column(DateTime, default=datetime.now, index=True)
    
    # 复合索引
    __table_args__ = (
        Index('idx_record_student_date', student_id, answer_time),
        Index('idx_record_student_correct', student_id, is_correct),
    )

class CodeRecord(Base):
    __tablename__ = 'code_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(20), ForeignKey('users.student_id'), index=True)
    code = Column(String(50))
    get_time = Column(DateTime, default=datetime.now, index=True)
    
    # 复合索引
    __table_args__ = (
        Index('idx_code_student_date', student_id, get_time),
    )

# Pydantic模型

class QuestionType(str, Enum):
    SINGLE = "single"
    MULTIPLE = "multiple"
    JUDGE = "judge"
    BLANK = "blank"
    ESSAY = "essay"

class Question(BaseModel):
    id: str
    type: QuestionType
    difficulty: int = Field(ge=1, le=3)
    content: str
    options: Optional[List[str]] = None
    answer: Union[str, List[str], bool, str]
    explanation: Optional[str] = None
    is_ai: bool = False # 是否是ai生成的题目
    related_question_id: Optional[str] = None # 如果是ai生成，那他是基于哪道题生成的
    enabled: bool = True # 是否启用该题目
    tags: List[str] = [] # 题目标签,用于分类和筛选

class QuestionResponse(BaseModel):
    id: str
    type: QuestionType
    difficulty: int
    content: str
    options: Optional[List[str]] = None

class LoginRequest(BaseModel):
    student_id: str
    name: Optional[str] = None

class AnswerRequest(BaseModel):
    question_id: str
    answer: Union[str, List[str], bool]  # 支持不同类型的答案

class Exam(Base):
    __tablename__ = 'exams'
    
    exam_id = Column(String(20), primary_key=True)
    student_id = Column(String(20), ForeignKey('users.student_id'), index=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False, index=True)
    submit_time = Column(DateTime, index=True)
    question_count = Column(Integer, nullable=False)
    current_progress = Column(Integer, default=0)  # 当前答题进度
    status = Column(String(20), default='进行中', index=True)  # 考试状态:进行中、已完成、已过期
    correct_count = Column(Integer, default=0)  # 正确题目数量
    
    # 复合索引
    __table_args__ = (
        Index('idx_exam_student_status', student_id, status),
        Index('idx_exam_student_submit', student_id, submit_time),
    )

class ExamRecord(Base):
    __tablename__ = 'exam_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(20), ForeignKey('users.student_id'), index=True)
    exam_id = Column(String(20), ForeignKey('exams.exam_id'), index=True)
    question_id = Column(String(20))
    student_answer = Column(String(500))  # 存储学生的答案,可能是字符串、列表或布尔值的JSON字符串
    is_correct = Column(Boolean, index=True)
    
    # 复合索引
    __table_args__ = (
        Index('idx_exam_record_exam_student', exam_id, student_id),
        Index('idx_exam_record_student_correct', student_id, is_correct),
    )

class AIChatRecord(Base):
    __tablename__ = 'ai_chat_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(20), ForeignKey('users.student_id'), index=True)
    question = Column(String(1000))  # 学生的问题
    answer = Column(String(5000))    # AI的回答
    chat_time = Column(DateTime, default=datetime.now, index=True)
    is_irrelevant = Column(Boolean, default=False, index=True)  # 是否是无关问题
    
    # 复合索引
    __table_args__ = (
        Index('idx_chat_student_time', student_id, chat_time),
        Index('idx_chat_student_irrelevant', student_id, is_irrelevant),
    )
