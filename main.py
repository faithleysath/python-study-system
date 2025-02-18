import os
default_json = """
{
    "admin": {
        "password": "admin123",
        "username": "admin"
    },
    "database": {
        "file": "openjudge.db",
        "max_overflow": 100,
        "pool_size": 50,
        "pool_timeout": 60
    },
    "deepseek": {
        "api_key": "sk-esadasdfsdf",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat"
    },
    "features": {
        "enable_exam": false,
        "enable_registration": false
    },
    "rate_limit": {
        "max_requests": 5,
        "window": 120
    },
    "system": {
        "correct_threshold": 3,
        "cycle_days": 3,
        "exam_duration": 10,
        "exam_question_count": 10,
        "pass_score": 60,
        "practice_threshold": 20,
        "question_range_days": 3
    },
    "QFluentWidgets": {
        "ThemeColor": "#ff009faa",
        "ThemeMode": "Auto"
    },
    "token": {
        "expire_minutes": 300
    }
}
"""
from paths import get_base_path, get_template_path
config_path = os.path.join(get_base_path(), 'config.json')
if os.path.exists(config_path) is False:
    with open(config_path, 'w') as f:
        f.write(default_json)
if os.path.exists(os.path.join(get_base_path(), 'data')) is False:
    os.mkdir(os.path.join(get_base_path(), 'data'))
if os.path.exists(os.path.join(get_base_path(), 'data', 'codes.txt')) is False:
    with open(os.path.join(get_base_path(), 'data', 'codes.txt'), 'w') as f:
        f.write('')

import sys
import webbrowser
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from qfluentwidgets import FluentWindow, FluentIcon, setTheme, Theme, MessageBox, NavigationAvatarWidget, NavigationItemPosition

from guiapp.server_interface import ServerInterface
from guiapp.config_interface import ConfigInterface
from guiapp.question_interface import QuestionInterface
from guiapp.database_interface import DatabaseInterface
from guiapp.config import cfg
from db import init_db


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(os.path.join(get_template_path(), 'logo.ico')))
        # 设置窗口属性
        self.resize(1000, 960)
        self.setWindowTitle('Python学习系统管理工具 v1.1.2')
        
        # 将窗口移动到屏幕中心
        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)
        
        # 创建子界面
        self.serverInterface = ServerInterface(self)
        self.serverInterface.setObjectName('serverInterface')
        
        self.configInterface = ConfigInterface(self)
        self.configInterface.setObjectName('configInterface')
        
        self.questionInterface = QuestionInterface(self)
        self.questionInterface.setObjectName('questionInterface')
        
        self.databaseInterface = DatabaseInterface(self)
        self.databaseInterface.setObjectName('databaseInterface')
        
        # 初始化窗口
        self.init_window()
        
    def init_window(self):
        # 添加子界面
        self.addSubInterface(self.serverInterface, FluentIcon.POWER_BUTTON, '服务器控制')
        self.addSubInterface(self.configInterface, FluentIcon.SETTING, '配置管理')
        self.addSubInterface(self.questionInterface, FluentIcon.EDIT, '题库管理')
        self.addSubInterface(self.databaseInterface, FluentIcon.LIBRARY, '数据管理')
        def onclick_avatar():
            w = MessageBox(
                "支持作者🥰",
                "个人开发不易，如果这个项目帮助到了您，可以考虑请作者喝一瓶快乐水🥤。您的支持就是作者开发和维护项目的动力🚀",
                self,
            )
            w.yesButton.setText("来啦老弟")
            w.cancelButton.setText("下次一定")
            if w.exec():
                webbrowser.open("https://github.com/faithleysath")

        self.navigationInterface.addWidget(
            routeKey="avatar",
            widget=NavigationAvatarWidget("laysath", os.path.join(get_template_path(), "avatar.png")),
            onClick=onclick_avatar,
            position=NavigationItemPosition.BOTTOM,
        )

    def closeEvent(self, event):
        """处理窗口关闭事件"""
        # 检查服务器是否在运行
        if self.serverInterface.server_thread and self.serverInterface.server_thread.isRunning():
            # 停止服务器
            self.serverInterface.stop_server()
            # 等待服务器完全停止
            self.serverInterface.server_thread.wait()
        
        # 调用父类的closeEvent
        super().closeEvent(event)


if __name__ == '__main__':
    init_db()
    # 启用高DPI缩放
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    app = QApplication(sys.argv)
    
    # 设置应用主题
    setTheme(Theme.AUTO)
    
    # 加载配置
    from qfluentwidgets import qconfig
    from guiapp.config import cfg
    qconfig.load(config_path, cfg)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())
