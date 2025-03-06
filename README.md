# OpenJudge - Python学习系统

OpenJudge是一个用于Python教学的综合学习系统，提供练习、考试、AI聊天等功能，帮助学生更有效地学习Python编程。

## 功能特性

- **练习模式**：随机抽取题目，学生可以反复练习直到掌握
- **考试模式**：支持限时考试，系统自动评分
- **AI聊天**：学生可提问Python学习相关问题，获得AI辅助
- **多题型支持**：单选题、多选题、判断题、填空题、问答题
- **IP绑定**：防止同一账号多地登录
- **数据统计**：记录学生练习和考试数据，提供分析报告
- **管理后台**：题库管理、用户管理、数据导出等

## 系统架构

- **Web应用**：基于FastAPI构建的Web服务，提供学习系统核心功能
  - 练习模式界面
  - 考试模式界面
  - AI聊天界面
  - 登录和用户管理
  - 题库系统
  
- **桌面管理工具**：基于PyQt5和QFluentWidgets构建的GUI应用
  - 服务器控制
  - 配置管理
  - 题库管理
  - 数据管理

## 技术栈

- **后端**：
  - FastAPI (Web框架)
  - SQLAlchemy (ORM)
  - JWT (认证)
  - Uvicorn (ASGI服务器)
  - DeepSeek API (AI聊天)

- **前端**：
  - HTML/CSS/JavaScript
  - 响应式设计
  
- **桌面工具**：
  - PyQt5
  - QFluentWidgets (UI组件)

- **数据存储**：
  - SQLite数据库
  - JSON文件 (题库存储)

## 安装指南

### 环境要求

- Python 3.8+
- pip包管理工具

### 步骤

1. 安装依赖项

```bash
pip install -r requirements.txt
```

2. 启动Web服务

```bash
python app.py
```

或使用管理工具启动：

```bash
python main.py
```

3. 访问系统

Web界面：http://localhost:8000

## 配置说明

系统使用`config.json`进行配置，主要配置项包括：

- **admin**: 管理员账户信息
- **database**: 数据库配置
- **deepseek**: AI聊天服务配置
- **features**: 功能开关
- **rate_limit**: 请求限流配置
- **system**: 系统参数设置
- **token**: 认证相关配置

第一次运行时会自动创建默认配置文件。

## 管理工具使用

系统附带GUI管理工具，提供以下功能：

1. **服务器控制**：启动/停止Web服务
2. **配置管理**：修改系统设置
3. **题库管理**：添加/编辑/删除题目
4. **数据管理**：查看用户数据、导出统计信息

## 打包发布

项目支持使用PyInstaller打包为独立可执行文件：

```bash
pyinstaller --onefile --add-data "static:static" --add-data "templates:templates" --icon=logo.ico --noconsole --name my_app --version-file=version_info.rc main.py
```

## 系统开发者

- 主要开发者：laysath

## 许可协议

详见LICENSE文件
