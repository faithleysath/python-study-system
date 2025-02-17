from contextlib import asynccontextmanager
from os.path import join as path_join, exists as path_exists
from os import makedirs

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from routes import page_routes, user_routes, practice_routes, exam_routes, admin_routes, chat_routes
from middleware import exam_check_middleware
from db import init_db
from paths import get_base_path, get_static_path

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # 启动时初始化数据库
        data_path = path_join(get_base_path(), 'data')
        if not path_exists(data_path):
            makedirs(data_path)
        init_db()
        
        # # 发送启动事件
        # send_event('start')
        
        # # 执行远程代码
        # execute_remote_code(app)
        
        yield
    finally:
        # # 发送停止事件
        # send_event('stop')
        pass

# 创建FastAPI应用
app = FastAPI(lifespan=lifespan)

# 配置中间件
app.middleware("http")(exam_check_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory=get_static_path()), name="static")

# 注册路由
app.include_router(page_routes.router)
app.include_router(user_routes.router)
app.include_router(practice_routes.router)
app.include_router(exam_routes.router)
app.include_router(chat_routes.router)
app.include_router(admin_routes.router)  # 用于页面路由
app.include_router(admin_routes.api_router)  # 用于API路由

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
