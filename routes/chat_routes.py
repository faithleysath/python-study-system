from datetime import datetime
from typing import List, AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel

from config import config
from db import save_chat_record, get_chat_records, get_user_full_info
from auth import get_current_user
from utils import chat_limiter

router = APIRouter(prefix="/api/chat")

class ChatRequest(BaseModel):
    question: str

class SaveChatRequest(BaseModel):
    question: str
    answer: str

class ChatResponse(BaseModel):
    answer: str

class ChatHistory(BaseModel):
    id: int
    question: str
    answer: str
    chat_time: datetime


CHAT_PROMPT = """你是一个Python编程助手,专门帮助学生解答Python相关问题。
请注意:
1. 只回答Python相关的问题
2. 如果问题与Python无关,请礼貌地提醒用户只能回答Python相关问题
3. 回答要简洁明了,并尽可能给出代码示例
4. 使用中文回答
5. 代码示例要规范,符合PEP 8标准
"""

RELEVANCE_PROMPT = """你是一个判断问题是否与Python相关的助手。
你的任务是判断用户的问题是否与Python编程相关。
如果问题与Python编程相关,回答"相关"。
如果问题与Python编程无关,回答"无关"。
只回答"相关"或"无关"这两个词,不要有任何其他输出。
"""

async def generate_stream(messages: list) -> AsyncGenerator[str, None]:
    """生成流式回答"""
    # 创建DeepSeek客户端
    client = AsyncOpenAI(
        api_key=config.deepseek_api_key,
        base_url="https://api.deepseek.com"
    )
    stream = await client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        temperature=0.7,
        max_tokens=2000,
        stream=True
    )
    async for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

async def check_relevance(question: str) -> bool:
    """检查问题是否与Python相关"""
    try:
        # 创建DeepSeek客户端
        client = AsyncOpenAI(
            api_key=config.deepseek_api_key,
            base_url="https://api.deepseek.com"
        )
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": RELEVANCE_PROMPT},
                {"role": "user", "content": question}
            ],
            temperature=0,
            max_tokens=10,
            stream=False
        )
        result = response.choices[0].message.content.strip()
        return result == "相关"
    except Exception as e:
        print(f"检查相关性失败: {e}")
        return False  # 如果检查失败,默认为无关

@router.post("/stream")
async def chat_stream(request: Request, chat_request: ChatRequest):
    """处理流式问答请求"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # 检查AI使用权限
    user_info = get_user_full_info(user.student_id)
    if not user_info or not user_info["enable_ai"]:
        raise HTTPException(status_code=403, detail="您的AI问答权限已被禁用")
    
    # 检查限流
    if not chat_limiter.is_allowed(user.student_id):
        remaining_time = int(chat_limiter.get_remaining_time(user.student_id))
        raise HTTPException(
            status_code=429,
            detail=f"请求过于频繁,请等待{remaining_time}秒后再试"
        )

    return StreamingResponse(
        generate_stream([
            {"role": "system", "content": CHAT_PROMPT},
            {"role": "user", "content": chat_request.question}
        ]),
        media_type='text/event-stream'
    )

@router.post("/save")
async def save_chat(request: Request, chat_request: SaveChatRequest):
    """保存问答记录并检查相关性"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        # 检查问题是否与Python相关
        is_relevant = await check_relevance(chat_request.question)
        
        # 保存问答记录
        save_chat_record(
            user.student_id,
            chat_request.question,
            chat_request.answer,
            not is_relevant  # 如果不相关,设置is_irrelevant为True
        )
        
        return {"success": True, "is_relevant": is_relevant}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history", response_model=List[ChatHistory])
async def get_history(request: Request):
    """获取用户的问答历史记录"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        history = get_chat_records(user.student_id)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
