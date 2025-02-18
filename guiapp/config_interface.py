import os
import time
from PyQt5.QtWidgets import QHBoxLayout, QWidget, QApplication
from PyQt5.QtCore import Qt, pyqtSignal
from paths import get_base_path
from qfluentwidgets import (SubtitleLabel, FluentIcon, InfoBar, BodyLabel,
                           SettingCardGroup, PushSettingCard, MessageBoxBase,
                           LineEdit, PasswordLineEdit, SwitchSettingCard,
                           SettingCard, ConfigItem, CompactSpinBox, EditableComboBox,
                           ExpandGroupSettingCard, ScrollArea,
                           SwitchButton, IndicatorPosition, ExpandLayout)
from qfluentwidgets import qconfig
from .config import cfg
from threading import Thread

class CustomEditableComboBox(EditableComboBox):
    ReturnPressed = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(250)
    def _onReturnPressed(self):
        super()._onReturnPressed()
        self.ReturnPressed.emit()

class SpinSettingCard(SettingCard):
    def __init__(self, icon, title, description, config: ConfigItem, parent=None):
        super().__init__(icon, title, description, parent)
        self.config = config
        self.spinbox = CompactSpinBox(self)
        self.hBoxLayout.addWidget(self.spinbox)
        self.hBoxLayout.addSpacing(12)
        self.spinbox.setValue(config.value)
        self.spinbox.valueChanged.connect(self.valueChanged)

    def valueChanged(self, value):
        self.config.value = value
        qconfig.save()

    def setValue(self, value):
        self.spinbox.setValue(value)
        self.valueChanged(value)

class LineEditSettingCard(SettingCard):
    def __init__(self, icon, title, description, config: ConfigItem, parent=None):
        super().__init__(icon, title, description, parent)
        self.config = config
        self.lineEdit = LineEdit(self)
        self.hBoxLayout.addWidget(self.lineEdit)
        self.hBoxLayout.addSpacing(12)
        self.lineEdit.setText(config.value)
        self.lineEdit.textChanged.connect(self.textChanged)

    def textChanged(self, value):
        self.config.value = value
        qconfig.save()

    def setText(self, value):
        self.lineEdit.setText(value)
        self.textChanged(value)

class ComboBoxSettingCard(SettingCard):
    itemChanged = pyqtSignal(str)
    def __init__(self, icon, title, description, config: ConfigItem, items, parent=None):
        super().__init__(icon, title, description, parent)
        self.config = config
        self.comboBox = CustomEditableComboBox(self)
        self.comboBox.addItems(items)
        self.hBoxLayout.addWidget(self.comboBox)
        self.hBoxLayout.addSpacing(12)
        self.comboBox.setCurrentText(config.value)
        self.comboBox.currentTextChanged.connect(self.textChanged)

    def textChanged(self, value):
        currentItemList = [self.comboBox.itemText(i) for i in range(self.comboBox.count())]
        if value not in currentItemList:
            return
        self.config.value = value
        qconfig.save()
        self.itemChanged.emit(value)

    def setCurrentText(self, value):
        self.comboBox.setCurrentText(value)
        self.textChanged(value)


class CustomAdminMessageBox(MessageBoxBase):
    """ Custom message box """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel('设置管理员账号')

        # 创建输入框
        self.usernameLabel = BodyLabel('用户名:', self)
        self.usernameEdit = LineEdit(self)
        self.usernameEdit.setText(cfg.adminUsername.value)
        
        self.passwordLabel = BodyLabel('密码:', self)
        self.passwordEdit = PasswordLineEdit(self)
        self.passwordEdit.setText(cfg.adminPassword.value)

        # 将组件添加到布局中
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addSpacing(16)
        self.viewLayout.addWidget(self.usernameLabel)
        self.viewLayout.addWidget(self.usernameEdit)
        self.viewLayout.addSpacing(12)
        self.viewLayout.addWidget(self.passwordLabel)
        self.viewLayout.addWidget(self.passwordEdit)
        self.viewLayout.addSpacing(16)

        # 设置对话框的最小宽度
        self.widget.setMinimumWidth(350)

    def getUsername(self):
        return self.usernameEdit.text()
    
    def getPassword(self):
        return self.passwordEdit.text()

def showAdminSettingDialog(window):
    w = CustomAdminMessageBox(window)
    if w.exec():
        # 保存设置
        cfg.adminUsername.value = w.getUsername()
        cfg.adminPassword.value = w.getPassword()
        qconfig.save()
        
        # 显示成功提示
        InfoBar.success(
            title='成功',
            content='管理员设置已更新',
            parent=window
        ).show()

class ConfigInterface(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.scrollWidget = QWidget()
        self.expandLayout = ExpandLayout(self.scrollWidget)
        
        self.setup_ui()
        # 连接数据库文件改变信号
        self.databaseFileCard.comboBox.ReturnPressed.connect(self.changeDatabaseFile)
        self.databaseFileCard.itemChanged.connect(self.restart_application)
        self.__initWidget()

        self.setStyleSheet("QScrollArea{background: transparent; border: none}")
        self.scrollWidget.setStyleSheet("QWidget{background: transparent}")

    def changeDatabaseFile(self):
        cfg.databaseFile.value = self.databaseFileCard.comboBox.currentText()
        qconfig.save()
        self.restart_application()
        
    def setup_ui(self):
        
        self.systemGroup = SettingCardGroup('系统设置', self.scrollWidget)
        
        # 管理员设置
        self.adminSettingCard = PushSettingCard(
            '设置', 
            FluentIcon.PEOPLE, 
            "管理员设置", 
            "设置管理员账号密码", 
            self.systemGroup
        )
        self.adminSettingCard.clicked.connect(self.open_admin_setting)
        
        # 注册功能开关
        self.enablingRegistrationCard = SwitchSettingCard(
            FluentIcon.PEOPLE, 
            "注册功能", 
            "启用/禁用用户注册", 
            cfg.featureEnableRegistration, 
            self.systemGroup
        )
        
        # 周期天数设置
        self.cycleDaysCard = SpinSettingCard(
            FluentIcon.CALENDAR,
            "周期天数",
            "设置系统周期天数",
            cfg.systemCycleDays,
            self.systemGroup
        )
        
        # 正确阈值设置
        self.correctThresholdCard = SpinSettingCard(
            FluentIcon.ACCEPT,
            "正确阈值",
            "达到此次数的正确题目在周期天数内不会重复出现",
            cfg.systemCorrectThreshold,
            self.systemGroup
        )
        
        # 练习阈值设置
        self.practiceThresholdCard = SpinSettingCard(
            FluentIcon.LIBRARY,
            "练习阈值",
            "必须在题目范围天数内做对此数量的题目才能参加考试",
            cfg.systemPracticeThreshold,
            self.systemGroup
        )

        # 创建考试设置卡片
        self.examGroup = ExamSettingCard(self.scrollWidget)
        
        # 获取数据库文件列表
        data_path = os.path.join(get_base_path(), 'data')
        db_files = [f for f in os.listdir(data_path) if f.endswith('.db')]
        
        # 数据库文件选择
        self.databaseFileCard = ComboBoxSettingCard(
            FluentIcon.DOCUMENT,
            "数据库文件",
            "选择要使用的数据库文件",
            cfg.databaseFile,
            db_files,
            self.systemGroup
        )
        
        # 添加所有系统设置卡片
        self.systemGroup.addSettingCard(self.adminSettingCard)
        self.systemGroup.addSettingCard(self.enablingRegistrationCard)
        self.systemGroup.addSettingCard(self.cycleDaysCard)
        self.systemGroup.addSettingCard(self.correctThresholdCard)
        self.systemGroup.addSettingCard(self.practiceThresholdCard)
        self.systemGroup.addSettingCard(self.databaseFileCard)

        # 创建高级设置卡片
        self.advancedGroup = AdvancedSettingCard(self.scrollWidget)
        
        # add setting card group to layout
        self.expandLayout.setSpacing(10)
        self.expandLayout.setContentsMargins(36, 10, 36, 0)
        self.expandLayout.addWidget(self.systemGroup)
        self.expandLayout.addWidget(self.examGroup)
        self.expandLayout.addWidget(self.advancedGroup)
        
    def __initWidget(self):
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 0, 0, 0)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        
        # initialize style
        self.scrollWidget.setObjectName('scrollWidget')

    def open_admin_setting(self):
        showAdminSettingDialog(self)
        
    def restart_application(self):
        """重启应用程序"""
        InfoBar.success(
            title='提示',
            content='数据库文件已更改，应用程序将重启',
            duration=2500,
            parent=self
        ).show()
        
        def delayed_restart():
            time.sleep(3)
            # 获取主窗口
            main_window = self.parent().parent()
            if main_window:
                # 关闭主窗口，这会触发closeEvent进行清理
                main_window.close()
                QApplication.quit(0)
        
        # 在新线程中执行重启操作
        Thread(target=delayed_restart).start()

class ExamSettingCard(ExpandGroupSettingCard):
    def __init__(self, parent=None):
        super().__init__(FluentIcon.EDUCATION, "考试设置", "设置考试相关参数", parent)
        
        # 考试功能开关
        self.enableExamLabel = BodyLabel("考试功能")
        self.enableExamSwitch = SwitchButton("关", self, IndicatorPosition.RIGHT)
        self.enableExamSwitch.setOnText("开")
        self.enableExamSwitch.setChecked(cfg.featureEnableExam.value)
        self.enableExamSwitch.checkedChanged.connect(lambda v: self._updateConfig(cfg.featureEnableExam, v))
        
        # 考试时长设置
        self.durationLabel = BodyLabel("考试时长（分钟）")
        self.durationBox = CompactSpinBox()
        self.durationBox.setValue(cfg.systemExamDuration.value)
        self.durationBox.valueChanged.connect(lambda v: self._updateConfig(cfg.systemExamDuration, v))
        
        # 考试题目数量
        self.questionCountLabel = BodyLabel("题目数量")
        self.questionCountBox = CompactSpinBox()
        self.questionCountBox.setValue(cfg.systemExamQuestionCount.value)
        self.questionCountBox.valueChanged.connect(lambda v: self._updateConfig(cfg.systemExamQuestionCount, v))
        
        # 及格分数
        self.passScoreLabel = BodyLabel("及格分数")
        self.passScoreBox = CompactSpinBox()
        self.passScoreBox.setValue(cfg.systemPassScore.value)
        self.passScoreBox.valueChanged.connect(lambda v: self._updateConfig(cfg.systemPassScore, v))
        
        # 题目范围天数
        self.rangeDaysLabel = BodyLabel("题目范围（天）")
        self.rangeDaysBox = CompactSpinBox()
        self.rangeDaysBox.setValue(cfg.systemQuestionRangeDays.value)
        self.rangeDaysBox.valueChanged.connect(lambda v: self._updateConfig(cfg.systemQuestionRangeDays, v))

        # 调整内部布局
        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        # 添加所有组件
        self.add(self.enableExamLabel, self.enableExamSwitch)
        self.add(self.durationLabel, self.durationBox)
        self.add(self.questionCountLabel, self.questionCountBox)
        self.add(self.passScoreLabel, self.passScoreBox)
        self.add(self.rangeDaysLabel, self.rangeDaysBox)

    def add(self, label, widget):
        w = QWidget()
        w.setFixedHeight(60)

        layout = QHBoxLayout(w)
        layout.setContentsMargins(48, 12, 48, 12)

        layout.addWidget(label)
        layout.addStretch(1)
        layout.addWidget(widget)

        self.addGroupWidget(w)
        
    def _updateConfig(self, config: ConfigItem, value):
        config.value = value
        qconfig.save()

class AdvancedSettingCard(ExpandGroupSettingCard):
    def __init__(self, parent=None):
        super().__init__(FluentIcon.DEVELOPER_TOOLS, "高级设置", "配置数据库和API相关参数", parent)
        
        # 数据库设置组
        self.dbPoolSizeLabel = BodyLabel("数据库连接池大小")
        self.dbPoolSizeBox = CompactSpinBox()
        self.dbPoolSizeBox.setValue(cfg.databasePoolSize.value)
        self.dbPoolSizeBox.valueChanged.connect(lambda v: self._updateConfig(cfg.databasePoolSize, v))
        
        self.dbMaxOverflowLabel = BodyLabel("最大溢出连接数")
        self.dbMaxOverflowBox = CompactSpinBox()
        self.dbMaxOverflowBox.setValue(cfg.databaseMaxOverflow.value)
        self.dbMaxOverflowBox.valueChanged.connect(lambda v: self._updateConfig(cfg.databaseMaxOverflow, v))
        
        self.dbTimeoutLabel = BodyLabel("连接超时时间（秒）")
        self.dbTimeoutBox = CompactSpinBox()
        self.dbTimeoutBox.setValue(cfg.databasePoolTimeout.value)
        self.dbTimeoutBox.valueChanged.connect(lambda v: self._updateConfig(cfg.databasePoolTimeout, v))
        
        # API设置组
        self.apiKeyLabel = BodyLabel("DeepSeek API密钥")
        self.apiKeyEdit = LineEdit()
        self.apiKeyEdit.setText(cfg.deepseekApiKey.value)
        self.apiKeyEdit.setFixedWidth(250)
        self.apiKeyEdit.textChanged.connect(lambda v: self._updateConfig(cfg.deepseekApiKey, v))

        self.baseUrlLabel = BodyLabel("DeepSeek Base URL")
        self.baseUrlEdit = LineEdit()
        self.baseUrlEdit.setText(cfg.deepseekBaseUrl.value)
        self.baseUrlEdit.setFixedWidth(250)
        self.baseUrlEdit.textChanged.connect(lambda v: self._updateConfig(cfg.deepseekBaseUrl, v))

        self.modelLabel = BodyLabel("DeepSeek 模型")
        self.modelEdit = LineEdit()
        self.modelEdit.setText(cfg.deepseekModel.value)
        self.modelEdit.setFixedWidth(250)
        self.modelEdit.textChanged.connect(lambda v: self._updateConfig(cfg.deepseekModel, v))
        
        # 速率限制设置组
        self.rateLimitLabel = BodyLabel("请求速率限制（次/窗口）")
        self.rateLimitBox = CompactSpinBox()
        self.rateLimitBox.setValue(cfg.rateLimitMaxRequests.value)
        self.rateLimitBox.valueChanged.connect(lambda v: self._updateConfig(cfg.rateLimitMaxRequests, v))
        
        self.windowSizeLabel = BodyLabel("限制窗口大小（秒）")
        self.windowSizeBox = CompactSpinBox()
        self.windowSizeBox.setValue(cfg.rateLimitWindow.value)
        self.windowSizeBox.valueChanged.connect(lambda v: self._updateConfig(cfg.rateLimitWindow, v))

        # 调整内部布局
        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        self.viewLayout.setSpacing(0)

        # 添加所有组件
        self.add(self.dbPoolSizeLabel, self.dbPoolSizeBox)
        self.add(self.dbMaxOverflowLabel, self.dbMaxOverflowBox)
        self.add(self.dbTimeoutLabel, self.dbTimeoutBox)
        self.add(self.apiKeyLabel, self.apiKeyEdit)
        self.add(self.baseUrlLabel, self.baseUrlEdit)
        self.add(self.modelLabel, self.modelEdit)
        self.add(self.rateLimitLabel, self.rateLimitBox)
        self.add(self.windowSizeLabel, self.windowSizeBox)

    def add(self, label, widget):
        w = QWidget()
        w.setFixedHeight(60)

        layout = QHBoxLayout(w)
        layout.setContentsMargins(48, 12, 48, 12)

        layout.addWidget(label)
        layout.addStretch(1)
        layout.addWidget(widget)

        self.addGroupWidget(w)
        
    def _updateConfig(self, config: ConfigItem, value):
        config.value = value
        qconfig.save()
