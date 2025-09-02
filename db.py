import json
import os
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from functools import lru_cache

from sqlalchemy import create_engine, func, and_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from config import config
from models import Base, User, Record, CodeRecord, Exam, ExamRecord, AIChatRecord
from questions import get_question_by_id

from paths import get_base_path

# 创建数据库目录
data_path = os.path.join(get_base_path(), 'data')
if not os.path.exists(data_path):
    os.makedirs(data_path)

# 创建数据库引擎
db_path = os.path.join(data_path, config.db_file)
engine = create_engine(
    f'sqlite:///{db_path}',
    poolclass=QueuePool,
    pool_size=config.db_pool_size,
    max_overflow=config.db_max_overflow,
    pool_timeout=config.db_pool_timeout
)

SessionLocal = sessionmaker(bind=engine)

@contextmanager
def get_db():
    """数据库会话上下文管理器"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def check_expired_exams():
    """检查并更新过期考试的状态"""
    with get_db() as db:
        current_time = datetime.now()
        # 查找所有进行中且已超过结束时间的考试
        expired_exams = db.query(Exam).filter(
            and_(
                Exam.status == "进行中",
                Exam.end_time < current_time
            )
        ).all()
        
        # 更新过期考试的状态
        for exam in expired_exams:
            exam.status = "已过期"
        
        if expired_exams:
            db.commit()

def start_exam_checker():
    """启动定期检查考试状态的线程"""
    def check_loop():
        while True:
            check_expired_exams()
            time.sleep(15)  # 每15秒检查一次
    
    checker_thread = threading.Thread(target=check_loop, daemon=True)
    checker_thread.start()

def init_db():
    """初始化数据库
    
    通过导入models模块中的所有模型(User, Record, CodeRecord, AIChatRecord等),
    这些模型类已经被注册到了Base.metadata中。
    当执行Base.metadata.create_all()时,
    SQLAlchemy会自动创建所有已注册模型对应的数据库表。
    """
    Base.metadata.create_all(engine)
    # 启动考试状态检查器
    start_exam_checker()

def save_chat_record(student_id: str, question: str, answer: str, is_irrelevant: bool = False) -> None:
    """保存AI问答记录"""
    with get_db() as db:
        chat_record = AIChatRecord(
            student_id=student_id,
            question=question,
            answer=answer,
            chat_time=datetime.now(),
            is_irrelevant=is_irrelevant
        )
        db.add(chat_record)

def get_chat_records(student_id: str) -> list:
    """获取学生的问答记录"""
    with get_db() as db:
        chats = db.query(AIChatRecord).filter(
            AIChatRecord.student_id == student_id
        ).order_by(AIChatRecord.chat_time.desc()).all()
        
        return [{
            "id": chat.id,
            "question": chat.question,
            "answer": chat.answer,
            "chat_time": chat.chat_time,
            "is_irrelevant": chat.is_irrelevant
        } for chat in chats]

def toggle_chat_relevance(chat_id: int) -> bool:
    """切换问题的相关性标记"""
    with get_db() as db:
        chat = db.query(AIChatRecord).filter(AIChatRecord.id == chat_id).first()
        if not chat:
            return False
        
        chat.is_irrelevant = not chat.is_irrelevant
        return True

def get_code_from_file() -> str:
    """从codes.txt文件中获取一个认证码并删除该行"""
    code = None
    codes_file = os.path.join(get_base_path(), 'data', 'codes.txt')
    
    if not os.path.exists(codes_file):
        return None
        
    try:
        with open(codes_file, 'r') as f:
            lines = f.readlines()
        
        if not lines:
            return None
            
        # 获取第一个非空认证码
        code = next((line.strip() for line in lines if line.strip()), None)
        
        if code:
            # 删除已使用的认证码
            with open(codes_file, 'w') as f:
                f.writelines(line for line in lines if line.strip() != code)
                
    except Exception as e:
        print(f"Error reading/writing codes file: {e}")
        return None
        
    return code

def check_today_exam_passed(db: Session, student_id: str) -> bool:
    """检查学生今天是否有通过的考试(正确率>=x%)"""
    today = datetime.now().date()
    exams = db.query(Exam).filter(
        and_(
            Exam.student_id == student_id,
            Exam.status == "已完成",
            Exam.submit_time >= today,
            Exam.submit_time < today + timedelta(days=1)
        )
    ).all()
    
    for exam in exams:
        if exam.correct_count / exam.question_count >= config.pass_score / 100:
            return True
    return False

def get_user_stats(student_id: str) -> dict:
    """获取用户统计信息"""
    with get_db() as db:
        # 获取总答题数和正确数
        total = db.query(Record).filter(Record.student_id == student_id).count()
        correct = db.query(Record).filter(
            Record.student_id == student_id,
            Record.is_correct == True
        ).count()
        
        # 获取今日认证码
        today = datetime.now().date()
        code_record = db.query(CodeRecord).filter(
            CodeRecord.student_id == student_id,
            CodeRecord.get_time >= today
        ).first()
        
        # 如果没有今日认证码,检查是否有通过的考试
        if not code_record and check_today_exam_passed(db, student_id):
            # 从文件获取新认证码
            new_code = get_code_from_file()
            if new_code:
                # 保存新认证码到数据库
                code_record = CodeRecord(
                    student_id=student_id,
                    code=new_code,
                    get_time=datetime.now()
                )
                db.add(code_record)
                db.commit()
        
        return {
            "totalQuestions": total,
            "correctRate": round((correct / total * 100) if total else 0),
            "todayCode": code_record.code if code_record else None
        }

def save_answer_record(student_id: str, question_id: str, is_correct: bool):
    """保存答题记录"""
    with get_db() as db:
        record = Record(
            student_id=student_id,
            question_id=question_id,
            is_correct=is_correct,
            answer_time=datetime.now()
        )
        db.add(record)

@lru_cache(maxsize=100)
def get_user_info(student_id: str) -> str:
    """获取用户姓名"""
    with get_db() as db:
        user = db.query(User).filter(User.student_id == student_id).first()
        return user.name if user else None

def get_user_full_info(student_id: str) -> dict:
    """获取用户完整信息"""
    with get_db() as db:
        user = db.query(User).filter(User.student_id == student_id).first()
        if not user:
            return None
        return {
            "name": user.name,
            "enable_ai": user.enable_ai,
            "enable_exam": user.enable_exam
        }

async def update_user_ai_permission(student_id: str, enable: bool) -> bool:
    """更新用户的AI使用权限
    
    Args:
        student_id: 学生ID
        enable: 是否允许使用AI
        
    Returns:
        bool: 更新是否成功
    """
    with get_db() as db:
        user = db.query(User).filter(User.student_id == student_id).first()
        if not user:
            return False
        user.enable_ai = enable
        db.commit()
        get_user_info.cache_clear()  # 清除缓存
        return True

def update_user_ai_permission_no_async(student_id: str, enable: bool) -> bool:
    """更新用户的AI使用权限
    
    Args:
        student_id: 学生ID
        enable: 是否允许使用AI
        
    Returns:
        bool: 更新是否成功
    """
    with get_db() as db:
        user = db.query(User).filter(User.student_id == student_id).first()
        if not user:
            return False
        user.enable_ai = enable
        db.commit()
        get_user_info.cache_clear()  # 清除缓存
        return True

def update_user_exam_permission_no_async(student_id: str, enable: bool) -> bool:
    """更新用户的考试权限
    
    Args:
        student_id: 学生ID
        enable: 是否允许参加考试
        
    Returns:
        bool: 更新是否成功
    """
    with get_db() as db:
        user = db.query(User).filter(User.student_id == student_id).first()
        if not user:
            return False
        user.enable_exam = enable
        db.commit()
        return True

def create_or_update_user(student_id: str, name: str, ip: str) -> None:
    """创建或更新用户信息"""
    with get_db() as db:
        user = db.query(User).filter(User.student_id == student_id).first()
        if not user:
            user = User(
                student_id=student_id,
                name=name,
                bound_ip=ip,
                bound_time=datetime.now()
            )
            db.add(user)
            get_user_info.cache_clear()
        else:
            user.bound_ip = ip
            user.bound_time = datetime.now()

def get_user_ip_info(student_id: str) -> tuple:
    """获取用户IP绑定信息"""
    with get_db() as db:
        user = db.query(User).filter(User.student_id == student_id).first()
        return (user.bound_ip, user.bound_time) if user else (None, None)

def get_ip_bound_user(ip: str) -> list:
    """获取今天绑定了该IP的所有用户ID"""
    with get_db() as db:
        today = datetime.now().date()
        users = db.query(User).filter(
            User.bound_ip == ip,
            User.bound_time >= today
        ).all()
        return [user.student_id for user in users]

def unbind_user_ip(student_id: str) -> bool:
    """解绑用户IP
    
    Args:
        student_id: 学生ID
        
    Returns:
        bool: 解绑是否成功
    """
    with get_db() as db:
        user = db.query(User).filter(User.student_id == student_id).first()
        if not user:
            return False
        user.bound_ip = None
        user.bound_time = None
        db.commit()
        return True

def delete_user(student_id: str) -> bool:
    """删除用户
    
    Args:
        student_id: 学生ID
        
    Returns:
        bool: 删除是否成功
    """
    with get_db() as db:
        user = db.query(User).filter(User.student_id == student_id).first()
        if not user:
            return False
        # 删除用户相关的所有记录
        db.query(Record).filter(Record.student_id == student_id).delete()
        db.query(CodeRecord).filter(CodeRecord.student_id == student_id).delete()
        db.query(ExamRecord).filter(ExamRecord.student_id == student_id).delete()
        db.query(Exam).filter(Exam.student_id == student_id).delete()
        db.query(AIChatRecord).filter(AIChatRecord.student_id == student_id).delete()
        # 最后删除用户
        db.delete(user)
        db.commit()
        return True

def get_excluded_questions(student_id: str) -> set:
    """获取学生x天内答对n次以上的题目ID"""
    with get_db() as db:
        one_week_ago = datetime.now() - timedelta(days=config.cycle_days)
        
        # 使用子查询获取答对n次以上的题目
        correct_records = db.query(Record.question_id).filter(
            Record.student_id == student_id,
            Record.is_correct == True,
            Record.answer_time > one_week_ago
        ).group_by(Record.question_id).having(
            func.count(Record.id) >= config.correct_threshold
        ).all()
        
        return {record[0] for record in correct_records}

def get_question_record(student_id: str, question_id: str) -> dict:
    """获取学生对特定题目的答题记录"""
    with get_db() as db:
        correct_count = db.query(Record).filter(
            Record.student_id == student_id,
            Record.question_id == question_id,
            Record.is_correct == True
        ).count()
        
        wrong_count = db.query(Record).filter(
            Record.student_id == student_id,
            Record.question_id == question_id,
            Record.is_correct == False
        ).count()
        
        return {
            "correct_count": correct_count,
            "wrong_count": wrong_count
        }

def get_ongoing_exam(student_id: str) -> dict:
    """检查是否有进行中的考试"""
    with get_db() as db:
        exam = db.query(Exam).filter(
            and_(
                Exam.student_id == student_id,
                Exam.status == "进行中"
            )
        ).first()
        
        if exam:
            # 检查是否超过截止时间
            if datetime.now() > exam.end_time:
                exam.status = "已过期"
                db.commit()
                return {
                    "has_ongoing_exam": False,
                    "correct_count": get_correct_questions_count(db, student_id),
                    "required_count": config.practice_threshold
                }
            return {
                "has_ongoing_exam": True,
                "exam_id": exam.exam_id
            }
        
        return {
            "has_ongoing_exam": False,
            "correct_count": get_correct_questions_count(db, student_id),
            "required_count": config.practice_threshold
        }

def get_correct_questions_count(db: Session, student_id: str) -> int:
    """获取一周内做对的不重复题目数量"""
    one_week_ago = datetime.now() - timedelta(days=config.question_range_days)
    return db.query(Record.question_id).distinct().filter(
        and_(
            Record.student_id == student_id,
            Record.is_correct == True,
            Record.answer_time >= one_week_ago
        )
    ).count()

def get_correct_questions_last_week(student_id: str) -> list:
    """获取一周内做对的不重复题目列表"""
    with get_db() as db:
        one_week_ago = datetime.now() - timedelta(days=config.question_range_days)
        correct_questions = db.query(Record.question_id).distinct().filter(
            and_(
                Record.student_id == student_id,
                Record.is_correct == True,
                Record.answer_time >= one_week_ago
            )
        ).all()
        return [q[0] for q in correct_questions]

def create_exam(student_id: str, selected_questions: list) -> dict:
    """创建新考试"""
    with get_db() as db:
        now = datetime.now()
        exam = Exam(
            exam_id = f"{student_id}_{now.strftime('%Y%m%d%H%M%S')}",
            student_id = student_id,
            start_time = now,
            end_time = now + timedelta(minutes=config.exam_duration),
            question_count = config.exam_question_count,
            current_progress = 0,
            status = "进行中"
        )
        
        exam_records = []
        for question_id in selected_questions:
            exam_records.append(
                ExamRecord(
                    student_id=student_id,
                    exam_id=exam.exam_id,
                    question_id=question_id
                )
            )
        
        db.add(exam)
        db.add_all(exam_records)
        db.commit()
        
        return {
            "exam_id": exam.exam_id,
            "end_time": exam.end_time.isoformat()
        }

def get_exam_questions(exam_id: str, student_id: str) -> dict:
    """获取考试题目"""
    with get_db() as db:
        exam = db.query(Exam).filter(
            and_(
                Exam.exam_id == exam_id,
                Exam.student_id == student_id
            )
        ).first()
        
        if not exam:
            return None
        
        exam_records = db.query(ExamRecord).filter(
            ExamRecord.exam_id == exam_id
        ).all()
        
        return {
            "questions": [r.question_id for r in exam_records],
            "current_progress": exam.current_progress,
            "end_time": exam.end_time.isoformat()
        }

def get_student_exams(student_id: str) -> list:
    """获取学生的已完成和已过期的考试记录"""
    with get_db() as db:
        exams = db.query(Exam).filter(
            and_(
                Exam.student_id == student_id,
                Exam.status.in_(["已完成", "已过期"])
            )
        ).order_by(Exam.start_time.desc()).all()
        
        return [{
            "exam_id": exam.exam_id,
            "start_time": exam.start_time.isoformat(),
            "end_time": exam.end_time.isoformat(),
            "submit_time": exam.submit_time.isoformat() if exam.submit_time else None,
            "status": exam.status,
            "question_count": exam.question_count,
            "correct_count": exam.correct_count
        } for exam in exams]

def submit_exam(exam_id: str) -> bool:
    """将未提交的考试标记为已提交
    
    Args:
        exam_id: 考试ID
        
    Returns:
        bool: 更新是否成功
    """
    with get_db() as db:
        exam = db.query(Exam).filter(
            and_(
                Exam.exam_id == exam_id,
                Exam.status == "进行中"
            )
        ).first()
        
        if not exam:
            return False
            
        exam.status = "已完成"
        exam.submit_time = datetime.now()
        db.commit()
        return True

def get_admin_exam_detail(exam_id: str) -> dict:
    """获取管理员查看的考试详情"""
    with get_db() as db:
        # 获取考试信息
        exam = db.query(Exam).filter(Exam.exam_id == exam_id).first()
        if not exam:
            return None
            
        # 获取学生信息
        student = db.query(User).filter(User.student_id == exam.student_id).first()
        if not student:
            return None
            
        # 获取考试详情
        exam_detail = get_exam_detail(exam_id, exam.student_id)
        if not exam_detail:
            return None
            
        return {
            "student_name": student.name,
            "student_id": student.student_id,
            "start_time": exam.start_time,
            "question_count": exam.question_count,
            "correct_count": exam.correct_count,
            "score": round(exam.correct_count / exam.question_count * 100, 1),
            "questions": exam_detail["questions"]
        }

def get_exam_detail(exam_id: str, student_id: str) -> dict:
    """获取考试的详细信息,包括题目内容、答案和解析"""
    with get_db() as db:
        exam = db.query(Exam).filter(
            and_(
                Exam.exam_id == exam_id,
                Exam.student_id == student_id
            )
        ).first()
        
        if not exam:
            return None
        
        exam_records = db.query(ExamRecord).filter(
            ExamRecord.exam_id == exam_id
        ).all()

        questions_info = []
        for record in exam_records:
            try:
                question = get_question_by_id(record.question_id, include_answer=True)
                question_dict = question.model_dump()
                question_dict["student_answer"] = json.loads(record.student_answer) if record.student_answer else None
                question_dict["is_correct"] = record.is_correct
                questions_info.append(question_dict)
            except:
                continue
        
        return {
            "exam_id": exam.exam_id,
            "start_time": exam.start_time.isoformat(),
            "end_time": exam.end_time.isoformat(),
            "submit_time": exam.submit_time.isoformat() if exam.submit_time else None,
            "status": exam.status,
            "current_progress": exam.current_progress,
            "question_count": len(questions_info),
            "correct_count": exam.correct_count,
            "questions": questions_info
        }

def update_exam_answer(exam_id: str, student_id: str, question_id: str, is_correct: bool, answer: dict) -> dict:
    """更新考试答案"""
    with get_db() as db:
        exam = db.query(Exam).filter(
            and_(
                Exam.exam_id == exam_id,
                Exam.student_id == student_id,
                Exam.status == "进行中"
            )
        ).first()
        
        if not exam:
            return None
        
        if datetime.now() > exam.end_time:
            exam.status = "已过期"
            db.commit()
            return None
        
        exam_record = db.query(ExamRecord).filter(
            and_(
                ExamRecord.exam_id == exam_id,
                ExamRecord.question_id == question_id
            )
        ).first()
        
        if not exam_record:
            return None
        
        exam_record.student_answer = json.dumps(answer)
        exam_record.is_correct = is_correct
        
        exam.current_progress += 1
        if is_correct:
            exam.correct_count += 1
        
        if exam.current_progress == exam.question_count:
            exam.status = "已完成"
            exam.submit_time = datetime.now()
        
        db.commit()
        
        return {
            "is_correct": is_correct,
            "current_progress": exam.current_progress,
            "exam_status": exam.status
        }
