import logging
import asyncio

import requests
import uvicorn
import webbrowser
from PyQt5.QtWidgets import (QFrame, QHBoxLayout, QVBoxLayout, QWidget)
from PyQt5.QtCore import QThread, pyqtSignal
from qfluentwidgets import (FluentIcon, PrimaryPushButton, 
                           PushButton, PlainTextEdit, InfoBar,
                           BodyLabel, CompactSpinBox)

from app import app as fastapi_app
from config import config

class QueueHandler(logging.Handler):
    def __init__(self, signal):
        super().__init__()
        self.signal = signal
        
    def emit(self, record):
        try:
            msg = self.format(record)
            self.signal.emit(msg)
        except Exception:
            self.handleError(record)

class ServerThread(QThread):
    output_received = pyqtSignal(str)
    
    def __init__(self, port=8000):
        super().__init__()
        self.server = None
        self.should_stop = False
        self.port = port
    
    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 创建并配置处理器
        queue_handler = QueueHandler(self.output_received)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        queue_handler.setFormatter(formatter)
        
        # 定义自定义日志配置字典
        log_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "custom": {
                    "()": lambda: formatter  # 直接使用已创建的格式化器
                }
            },
            "handlers": {
                "custom_handler": {
                    "class": "guiapp.server_interface.QueueHandler",  # 通过全路径引用你的类
                    "formatter": "custom",
                    "signal": self.output_received  # 传递你的信号对象
                }
            },
            "loggers": {
                "uvicorn": {
                    "handlers": ["custom_handler"],
                    "level": "INFO",
                    "propagate": False
                },
                "uvicorn.error": {
                    "handlers": ["custom_handler"],
                    "level": "INFO",
                    "propagate": False
                },
                "uvicorn.access": {
                    "handlers": ["custom_handler"],
                    "level": "INFO",
                    "propagate": False
                }
            }
        }
        
        # 配置uvicorn
        config = uvicorn.Config(
            fastapi_app,
            host="0.0.0.0",
            port=self.port,
            log_level="info",
            loop="asyncio",
            log_config=log_config  # 关键：通过配置字典注入自定义处理器
        )
        self.server = uvicorn.Server(config)
        
        # 添加关闭事件处理
        loop.create_task(self.check_stop())
        
        # 运行服务器
        loop.run_until_complete(self.server.serve())
    
    async def check_stop(self):
        """检查是否应该停止服务器"""
        while not self.should_stop:
            await asyncio.sleep(0.1)
        if self.server:
            self.server.should_exit = True
    
    def stop(self):
        """触发服务器停止"""
        self.should_stop = True
        self.wait()    

class ServerInterface(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.server_thread = None
        self.setup_ui()
    
    def check_authorization(self):
        """检查是否有权限启动服务器"""
        try:
            url = f"https://myapp.laysath.cn/api/event/start?app=openjudge&version={config.version}"
            response = requests.get(url, timeout=0.1)
            if response.status_code == 200:
                config.detail_info = response.json()["data"]["detail_info"]
                return True
        except Exception as e:
            return False
        return False
        
    def setup_ui(self):
        self.vBoxLayout = QVBoxLayout(self)
        
        # 按钮区域
        self.buttonWidget = QWidget(self)
        self.buttonLayout = QHBoxLayout(self.buttonWidget)
        
        # 添加端口号控制
        self.portLabel = BodyLabel('端口号:', self)
        self.portSpinBox = CompactSpinBox(self)
        self.portSpinBox.setRange(1024, 65535)
        self.portSpinBox.setValue(8000)
        
        self.startButton = PrimaryPushButton('启动服务器', self)
        self.stopButton = PushButton('停止服务器', self)
        self.stopButton.setEnabled(False)
        
        self.openAdminButton = PushButton('打开后台', self)
        self.openAdminButton.setIcon(FluentIcon.LINK)
        self.openAdminButton.clicked.connect(self.open_admin)
        self.openAdminButton.setEnabled(False)
        
        self.buttonLayout.addWidget(self.portLabel)
        self.buttonLayout.addWidget(self.portSpinBox)
        self.buttonLayout.addWidget(self.startButton)
        self.buttonLayout.addWidget(self.stopButton)
        self.buttonLayout.addWidget(self.openAdminButton)
        self.buttonLayout.addStretch(1)
        
        # 日志显示区域
        self.logViewer = PlainTextEdit(self)
        self.logViewer.setReadOnly(True)
        self.logViewer.setPlaceholderText("服务器日志输出...")
        
        self.vBoxLayout.addWidget(self.buttonWidget)
        self.vBoxLayout.addWidget(self.logViewer)
        
        # 连接信号
        self.startButton.clicked.connect(self.start_server)
        self.stopButton.clicked.connect(self.stop_server)
        
    def start_server(self):
        if not self.check_authorization():
            InfoBar.error(
                title='错误',
                content='未授权,无法启动服务器',
                duration=3000,
                parent=self
            ).show()
            return
            
        if not self.server_thread:
            port = self.portSpinBox.value()
            self.server_thread = ServerThread(port)
            self.server_thread.output_received.connect(self.append_log)
            self.server_thread.finished.connect(self.on_server_stopped)
            self.server_thread.start()
            
            self.startButton.setEnabled(False)
            self.stopButton.setEnabled(True)
            self.logViewer.clear()
            self.logViewer.appendPlainText("正在启动服务器...")
            
            InfoBar.success(
                title='服务器',
                content=f'正在启动服务器(端口:{port})',
                duration=1500,
                parent=self
            ).show()
            
    def stop_server(self):
        if self.server_thread:
            try:
                url = f"https://myapp.laysath.cn/api/event/stop?app=openjudge&version={config.version}"
                requests.get(url, timeout=0.1)
            except Exception as e:
                pass
            self.logViewer.appendPlainText("正在停止服务器...")
            self.server_thread.stop()
            self.stopButton.setEnabled(False)
            
            InfoBar.info(
                title='服务器',
                content='正在停止服务器',
                parent=self
            ).show()
            
    def on_server_stopped(self):
        self.server_thread = None
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.openAdminButton.setEnabled(False)
        self.logViewer.appendPlainText("服务器已停止")
        
        InfoBar.success(
            title='服务器',
            content='服务器已成功停止',
            duration=2000,
            parent=self
        ).show()
        
    def append_log(self, text: str):
        self.logViewer.appendPlainText(text)
        if "Application startup complete" in text:
            self.openAdminButton.setEnabled(True)
            
    def open_admin(self):
        port = self.portSpinBox.value()
        webbrowser.open(f'http://localhost:{port}/admin/login')
