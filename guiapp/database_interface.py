from PyQt5.QtWidgets import (QFrame, QHBoxLayout, QVBoxLayout, QWidget, 
                            QTableWidgetItem, QStackedWidget)
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QColor
from qfluentwidgets import (SubtitleLabel, FluentIcon, PrimaryPushButton, 
                           PushButton, InfoBar, BodyLabel, SearchLineEdit,
                           TableWidget, TransparentToolButton,
                           FlowLayout, MessageBoxBase, CardWidget,
                           SingleDirectionScrollArea, SwitchButton,
                           FastCalendarPicker, PrimarySplitPushButton,
                           RoundMenu, Action, TabBar)

from db import get_admin_exam_detail, get_db, update_user_ai_permission_no_async, update_user_exam_permission_no_async, submit_exam
from models import Exam, User

class StatisticsCard(CardWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel(title, self)
        self.contentLabel = BodyLabel('加载中...', self)
        
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.addWidget(self.titleLabel)
        self.vBoxLayout.addWidget(self.contentLabel)
        
    def setValue(self, value: str):
        self.contentLabel.setText(value)

class UserTable(TableWidget):
    """用户管理表格"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(7)  # 增加一列用于解绑按钮
        self.setHorizontalHeaderLabels(['学号', '姓名', 'IP地址', '绑定时间', 'AI权限', '考试权限', '操作'])

        # 启用排序和多选
        self.setSortingEnabled(True)
        self.setSelectionBehavior(self.SelectRows)
        
        # 设置列宽
        self.setColumnWidth(0, 150)  # 学号
        self.setColumnWidth(1, 150)  # 姓名
        self.setColumnWidth(2, 150)  # IP
        self.setColumnWidth(3, 200)  # 绑定时间
        self.setColumnWidth(4, 100)  # AI权限
        self.setColumnWidth(5, 100)  # 考试权限
        self.setColumnWidth(6, 100)  # 操作
        
    def add_user(self, user: dict):
        """添加用户到表格"""
        row = self.rowCount()
        self.insertRow(row)
        
        # 添加数据
        self.setItem(row, 0, QTableWidgetItem(user['student_id']))
        self.setItem(row, 1, QTableWidgetItem(user['name']))
        self.setItem(row, 2, QTableWidgetItem(user['bound_ip'] or '未绑定'))
        self.setItem(row, 3, QTableWidgetItem(user['bound_time'].strftime('%Y-%m-%d %H:%M:%S') if user['bound_time'] else '未绑定'))
        
        # AI权限开关
        aiSwitch = SwitchButton()
        aiSwitch.setChecked(user['enable_ai'])
        aiSwitch.setProperty('student_id', user['student_id'])
        aiSwitch.setOffText("禁用")
        aiSwitch.setOnText("启用")
        # 连接信号
        aiSwitch.checkedChanged.connect(
            lambda checked, student_id=user['student_id']: 
            self.parent().parent().parent().update_user_ai_permission(student_id, checked)
        )
        
        # 创建容器并添加开关按钮
        aiContainer = QWidget()
        aiLayout = QHBoxLayout(aiContainer)
        aiLayout.setContentsMargins(0, 0, 0, 0)
        aiLayout.addWidget(aiSwitch)
        aiLayout.addStretch()
        
        self.setCellWidget(row, 4, aiContainer)
        
        # 考试权限开关
        examSwitch = SwitchButton()
        examSwitch.setChecked(user['enable_exam'])
        examSwitch.setProperty('student_id', user['student_id'])
        examSwitch.setOffText("禁用")
        examSwitch.setOnText("启用")
        # 连接信号
        examSwitch.checkedChanged.connect(
            lambda checked, student_id=user['student_id']: 
            self.parent().parent().parent().update_user_exam_permission(student_id, checked)
        )
        
        # 创建容器并添加开关按钮
        examContainer = QWidget()
        examLayout = QHBoxLayout(examContainer)
        examLayout.setContentsMargins(0, 0, 0, 0)
        examLayout.addWidget(examSwitch)
        examLayout.addStretch()
        
        self.setCellWidget(row, 5, examContainer)
        
        # 添加操作按钮容器
        btnContainer = QWidget()
        btnLayout = QHBoxLayout(btnContainer)
        btnLayout.setContentsMargins(0, 0, 0, 0)
        
        # 解绑按钮
        unbindBtn = TransparentToolButton(FluentIcon.REMOVE)
        unbindBtn.setProperty('student_id', user['student_id'])
        unbindBtn.clicked.connect(
            lambda checked, student_id=user['student_id']: 
            self.parent().parent().parent().unbind_user_ip(student_id)
        )
        
        # 删除按钮
        deleteBtn = TransparentToolButton(FluentIcon.DELETE)
        deleteBtn.setProperty('student_id', user['student_id'])
        deleteBtn.clicked.connect(
            lambda checked, student_id=user['student_id']: 
            self.parent().parent().parent().show_delete_confirm(student_id)
        )
        
        btnLayout.addWidget(unbindBtn)
        btnLayout.addWidget(deleteBtn)
        btnLayout.addStretch()
        
        self.setCellWidget(row, 6, btnContainer)

class ExamTable(TableWidget):
    """考试记录表格"""
    viewExam = pyqtSignal(str)  # 发送考试ID信号
    submitExam = pyqtSignal(str)  # 发送考试ID信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(7)
        self.setHorizontalHeaderLabels(['考试ID', '学号', '姓名', '开始时间', '提交时间', '得分', '操作'])
        
        # 启用排序和多选
        self.setSortingEnabled(True)
        self.setSelectionBehavior(self.SelectRows)
        
        # 设置列宽
        self.setColumnWidth(0, 200)  # 考试ID
        self.setColumnWidth(1, 100)  # 学号
        self.setColumnWidth(2, 100)  # 姓名
        self.setColumnWidth(3, 150)  # 开始时间
        self.setColumnWidth(4, 150)  # 提交时间
        self.setColumnWidth(5, 100)  # 得分
        self.setColumnWidth(6, 100)  # 操作
        
    def add_exam(self, exam: dict):
        """添加考试记录到表格"""
        row = self.rowCount()
        self.insertRow(row)
        
        # 添加数据并设置颜色
        items = [
            QTableWidgetItem(exam['exam_id']),
            QTableWidgetItem(exam['student_id']),
            QTableWidgetItem(exam['student_name']),
            QTableWidgetItem(exam['start_time'].strftime('%Y-%m-%d %H:%M:%S')),
            QTableWidgetItem(exam['submit_time'].strftime('%Y-%m-%d %H:%M:%S') if exam['submit_time'] else '未提交'),
        ]
        
        score = round(exam['correct_count'] / exam['question_count'] * 100, 1) if exam['submit_time'] else 0
        score_item = QTableWidgetItem(f"{score}分")
        
        # 设置颜色
        if not exam['submit_time']:
            color = '#F0F0F0'  # 灰色，未提交
        elif score >= 60:
            color = '#E3F4E1'  # 绿色，通过
        else:
            color = '#FBE9E7'  # 红色，未通过
            
        # 应用颜色到所有列
        for i, item in enumerate(items):
            item.setBackground(QColor(color))
            self.setItem(row, i, item)
        
        score_item.setBackground(QColor(color))
        self.setItem(row, 5, score_item)
        
        # 添加操作按钮
        btnWidget = QWidget()
        layout = QHBoxLayout(btnWidget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        viewBtn = TransparentToolButton(FluentIcon.VIEW)
        viewBtn.setProperty('exam_id', exam['exam_id'])
        viewBtn.clicked.connect(lambda: self.viewExam.emit(exam['exam_id']))
        layout.addWidget(viewBtn)
        
        # 如果是进行中的考试，添加提交按钮
        if not exam['submit_time']:
            submitBtn = TransparentToolButton(FluentIcon.SEND)
            submitBtn.setProperty('exam_id', exam['exam_id'])
            submitBtn.clicked.connect(lambda: self.submitExam.emit(exam['exam_id']))
            layout.addWidget(submitBtn)
        
        layout.addStretch()
        self.setCellWidget(row, 6, btnWidget)

class DatabaseInterface(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        self.vBoxLayout = QVBoxLayout(self)
        
        # 统计卡片
        self.cardWidget = QWidget(self)
        self.flowLayout = FlowLayout(self.cardWidget)
        
        self.userCard = StatisticsCard('用户总数', self)
        self.examCard = StatisticsCard('考试次数', self)
        self.passCard = StatisticsCard('通过率', self)
        
        self.flowLayout.addWidget(self.userCard)
        self.flowLayout.addWidget(self.examCard)
        self.flowLayout.addWidget(self.passCard)
        
        # 数据表切换
        self.tabBar = TabBar(self)
        self.stackedWidget = QStackedWidget(self)
        
        # 添加标签页
        self.tabBar.addTab('users', text='用户管理', icon=FluentIcon.PEOPLE)
        self.tabBar.addTab('exams', text='考试记录', icon=FluentIcon.STOP_WATCH)
        
        # 用户管理页面
        self.userPage = QWidget(self)
        self.userLayout = QVBoxLayout(self.userPage)
        
        # 用户筛选控件
        self.userFilterWidget = QWidget(self)
        self.userFilterLayout = QHBoxLayout(self.userFilterWidget)
        self.userFilterLayout.setContentsMargins(0, 0, 0, 0)
        
        # 学号筛选
        self.userIdFilter = SearchLineEdit(self)
        self.userIdFilter.setPlaceholderText('按学号筛选...')
        self.userIdFilter.textChanged.connect(self.filter_users)
        
        # IP筛选
        self.ipFilter = SearchLineEdit(self)
        self.ipFilter.setPlaceholderText('按IP筛选...')
        self.ipFilter.textChanged.connect(self.filter_users)
        
        # 清除筛选按钮
        self.clearUserFilterButton = PushButton('清除筛选', self)
        self.clearUserFilterButton.clicked.connect(self.clear_user_filters)
        
        # 刷新按钮
        self.refreshUserButton = PushButton('刷新数据', self)
        self.refreshUserButton.setIcon(FluentIcon.SYNC)
        self.refreshUserButton.clicked.connect(self.refresh_data)
        
        # 批量操作按钮
        self.batchUserButton = PrimarySplitPushButton('批量操作', self)
        menu = RoundMenu(parent=self.batchUserButton)
        menu.addAction(Action(FluentIcon.REMOVE, '批量解绑IP', triggered=self.batch_unbind_ip))
        menu.addAction(Action(FluentIcon.DELETE, '批量删除', triggered=self.batch_delete_users))
        self.batchUserButton.setFlyout(menu)
        
        self.userFilterLayout.addWidget(BodyLabel('学号:', self))
        self.userFilterLayout.addWidget(self.userIdFilter)
        self.userFilterLayout.addSpacing(10)
        self.userFilterLayout.addWidget(BodyLabel('IP:', self))
        self.userFilterLayout.addWidget(self.ipFilter)
        self.userFilterLayout.addSpacing(10)
        self.userFilterLayout.addWidget(self.clearUserFilterButton)
        self.userFilterLayout.addSpacing(10)
        self.userFilterLayout.addWidget(self.refreshUserButton)
        self.userFilterLayout.addWidget(self.batchUserButton)
        self.userFilterLayout.addStretch(1)
        
        self.userLayout.addWidget(self.userFilterWidget)
        self.userTable = UserTable(self)
        self.userLayout.addWidget(self.userTable)
        
        # 考试记录页面
        self.examPage = QWidget(self)
        self.examLayout = QVBoxLayout(self.examPage)
        
        # 筛选控件
        self.filterWidget = QWidget(self)
        self.filterLayout = QHBoxLayout(self.filterWidget)
        self.filterLayout.setContentsMargins(0, 0, 0, 0)
        
        # 学号筛选
        self.studentIdFilter = SearchLineEdit(self)
        self.studentIdFilter.setPlaceholderText('按学号筛选...')
        self.studentIdFilter.textChanged.connect(self.filter_exams)
        
        # 日期筛选
        self.dateFilter = FastCalendarPicker(self)
        self.dateFilter.setDateFormat('yyyy-MM-dd')
        self.dateFilter.dateChanged.connect(self.filter_exams)
        
        # 清除筛选按钮
        self.clearFilterButton = PushButton('清除筛选', self)
        self.clearFilterButton.clicked.connect(self.clear_filters)
        
        self.filterLayout.addWidget(BodyLabel('学号:', self))
        self.filterLayout.addWidget(self.studentIdFilter)
        self.filterLayout.addSpacing(10)
        self.filterLayout.addWidget(BodyLabel('开始日期:', self))
        self.filterLayout.addWidget(self.dateFilter)
        self.filterLayout.addSpacing(10)
        self.filterLayout.addWidget(self.clearFilterButton)
        self.filterLayout.addSpacing(10)
        
        # 添加刷新按钮
        self.refreshButton = PushButton('刷新数据', self)
        self.refreshButton.setIcon(FluentIcon.SYNC)
        self.refreshButton.clicked.connect(self.refresh_data)
        self.filterLayout.addWidget(self.refreshButton)

        # 添加一键提交按钮
        self.submitAllButton = PrimaryPushButton('一键提交未交', self)
        self.submitAllButton.clicked.connect(self.submit_all_unsubmitted)
        self.filterLayout.addWidget(self.submitAllButton)
        
        self.filterLayout.addStretch(1)
        
        self.examLayout.addWidget(self.filterWidget)
        self.examTable = ExamTable(self)
        self.examLayout.addWidget(self.examTable)
        
        self.stackedWidget.addWidget(self.userPage)
        self.stackedWidget.addWidget(self.examPage)
        
        # 连接信号
        self.tabBar.currentChanged.connect(self.stackedWidget.setCurrentIndex)
        self.examTable.viewExam.connect(self.show_exam_detail)
        self.examTable.submitExam.connect(self.submit_exam)
        
        self.vBoxLayout.addWidget(self.cardWidget)
        self.vBoxLayout.addWidget(self.tabBar)
        self.vBoxLayout.addWidget(self.stackedWidget)
    
    def show_delete_confirm(self, student_id: str):
        """显示删除确认对话框"""
        dialog = MessageBoxBase(self)
        dialog.titleLabel = SubtitleLabel('删除确认')
        
        # 添加警告信息
        warningLabel = BodyLabel(
            f'确定要删除学号为 {student_id} 的用户吗？\n'
            '该操作将删除该用户的所有数据，包括考试记录、答题记录等。\n'
            '此操作不可恢复！'
        )
        warningLabel.setStyleSheet('color: red')
        
        dialog.viewLayout.addWidget(dialog.titleLabel)
        dialog.viewLayout.addWidget(warningLabel)
        
        # 设置对话框的最小宽度
        dialog.widget.setMinimumWidth(400)
        
        if dialog.exec():
            self.delete_user(student_id)
            
    def delete_user(self, student_id: str):
        """删除用户"""
        try:
            from db import delete_user
            success = delete_user(student_id)
            if success:
                InfoBar.success(
                    title='成功',
                    content=f'已删除用户 {student_id}',
                    parent=self
                ).show()
                # 刷新数据
                self.refresh_data()
            else:
                InfoBar.error(
                    title='错误',
                    content=f'删除用户失败',
                    parent=self
                ).show()
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=f'删除用户失败: {str(e)}',
                parent=self
            ).show()
    
    def batch_unbind_ip(self):
        """批量解绑IP"""
        try:
            selected_rows = set(item.row() for item in self.userTable.selectedItems())
            
            if not selected_rows:
                InfoBar.warning(
                    title='提示',
                    content='请先选择要操作的用户',
                    parent=self
                ).show()
                return
            
            count = 0
            for row in selected_rows:
                if not self.userTable.isRowHidden(row):
                    student_id_item = self.userTable.item(row, 0)
                    if student_id_item:
                        student_id = student_id_item.text()
                        from db import unbind_user_ip
                        if unbind_user_ip(student_id):
                            count += 1
            
            if count > 0:
                InfoBar.success(
                    title='成功',
                    content=f'已解绑 {count} 个用户的IP',
                    parent=self
                ).show()
                self.refresh_data()
            else:
                InfoBar.info(
                    title='提示',
                    content='没有需要解绑的IP',
                    parent=self
                ).show()
                
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=f'批量解绑IP失败: {str(e)}',
                parent=self
            ).show()
    
    def batch_delete_users(self):
        """批量删除用户"""
        selected_rows = set(item.row() for item in self.userTable.selectedItems())
        
        if not selected_rows:
            InfoBar.warning(
                title='提示',
                content='请先选择要删除的用户',
                parent=self
            ).show()
            return
        
        # 创建确认对话框
        dialog = MessageBoxBase(self)
        dialog.titleLabel = SubtitleLabel('批量删除确认')
        
        # 添加警告信息
        warningLabel = BodyLabel(
            f'确定要删除选中的 {len(selected_rows)} 个用户吗？\n'
            '该操作将删除这些用户的所有数据，包括考试记录、答题记录等。\n'
            '此操作不可恢复！'
        )
        warningLabel.setStyleSheet('color: red')
        
        dialog.viewLayout.addWidget(dialog.titleLabel)
        dialog.viewLayout.addWidget(warningLabel)
        dialog.widget.setMinimumWidth(400)
        
        if dialog.exec():
            try:
                count = 0
                from db import delete_user
                for row in selected_rows:
                    if not self.userTable.isRowHidden(row):
                        student_id_item = self.userTable.item(row, 0)
                        if student_id_item:
                            student_id = student_id_item.text()
                            if delete_user(student_id):
                                count += 1
                
                if count > 0:
                    InfoBar.success(
                        title='成功',
                        content=f'已删除 {count} 个用户',
                        parent=self
                    ).show()
                    self.refresh_data()
                else:
                    InfoBar.error(
                        title='错误',
                        content='删除用户失败',
                        parent=self
                    ).show()
                    
            except Exception as e:
                InfoBar.error(
                    title='错误',
                    content=f'批量删除失败: {str(e)}',
                    parent=self
                ).show()
    
    def update_user_ai_permission(self, student_id: str, enable: bool):
        """更新用户AI权限"""
        try:
            success = update_user_ai_permission_no_async(student_id, enable)
            if success:
                InfoBar.success(
                    title='成功',
                    content=f'已{"启用" if enable else "禁用"} {student_id} 的AI权限',
                    parent=self
                ).show()
            else:
                InfoBar.error(
                    title='错误',
                    content=f'更新AI权限失败',
                    parent=self
                ).show()
        except Exception as e:
            InfoBar.error(
                title='错误',
                    content=f'更新AI权限失败: {str(e)}',
                    parent=self
                ).show()
    
    def update_user_exam_permission(self, student_id: str, enable: bool):
        """更新用户考试权限"""
        try:
            success = update_user_exam_permission_no_async(student_id, enable)
            if success:
                InfoBar.success(
                    title='成功',
                    content=f'已{"启用" if enable else "禁用"} {student_id} 的考试权限',
                    parent=self
                ).show()
            else:
                InfoBar.error(
                    title='错误',
                    content=f'更新考试权限失败',
                    parent=self
                ).show()
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=f'更新考试权限失败: {str(e)}',
                parent=self
            ).show()
            
    def unbind_user_ip(self, student_id: str):
        """解绑用户IP"""
        try:
            from db import unbind_user_ip
            success = unbind_user_ip(student_id)
            if success:
                InfoBar.success(
                    title='成功',
                    content=f'已解绑 {student_id} 的IP',
                    parent=self
                ).show()
                # 刷新数据
                self.refresh_data()
            else:
                InfoBar.error(
                    title='错误',
                    content=f'解绑IP失败',
                    parent=self
                ).show()
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=f'解绑IP失败: {str(e)}',
                parent=self
            ).show()
        
    def clear_data(self):
        """清空所有数据"""
        # 清空统计卡片
        self.userCard.setValue('0')
        self.examCard.setValue('0')
        self.passCard.setValue('0%')
        
        # 清空表格
        self.userTable.clearContents()
        self.userTable.setRowCount(0)
        self.examTable.clearContents()
        self.examTable.setRowCount(0)
        
    def submit_all_unsubmitted(self):
        """一键提交所有未提交的考试"""
        try:
            selected_rows = set(item.row() for item in self.examTable.selectedItems())
            
            if not selected_rows:
                InfoBar.warning(
                    title='提示',
                    content='请先选择要提交的考试',
                    parent=self
                ).show()
                return
            
            submitted_count = 0
            for row in selected_rows:
                if not self.examTable.isRowHidden(row):
                    # 检查是否未提交
                    submit_time_item = self.examTable.item(row, 4)  # 提交时间在第5列
                    if submit_time_item and submit_time_item.text() == '未提交':
                        # 获取考试ID
                        exam_id_item = self.examTable.item(row, 0)  # 考试ID在第1列
                        if exam_id_item:
                            exam_id = exam_id_item.text()
                            if submit_exam(exam_id):
                                submitted_count += 1
            
            if submitted_count > 0:
                InfoBar.success(
                    title='成功',
                    content=f'已提交 {submitted_count} 个未交考试',
                    parent=self
                ).show()
                # 刷新数据
                self.refresh_data()
            else:
                InfoBar.info(
                    title='提示',
                    content='没有需要提交的考试',
                    parent=self
                ).show()
                
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=f'批量提交失败: {str(e)}',
                parent=self
            ).show()
    
    def clear_user_filters(self):
        """清除用户筛选条件"""
        self.userIdFilter.clear()
        self.ipFilter.clear()
        self.filter_users()
        
    def filter_users(self):
        """根据筛选条件过滤用户"""
        user_id = self.userIdFilter.text().strip().lower()
        ip = self.ipFilter.text().strip().lower()
        
        for row in range(self.userTable.rowCount()):
            show_row = True
            
            # 检查学号筛选条件
            if user_id:
                user_id_item = self.userTable.item(row, 0)  # 学号在第1列
                if not user_id_item or user_id not in user_id_item.text().lower():
                    show_row = False
            
            # 检查IP筛选条件
            if show_row and ip:
                ip_item = self.userTable.item(row, 2)  # IP在第3列
                if not ip_item or ip not in ip_item.text().lower():
                    show_row = False
            
            # 显示或隐藏行
            self.userTable.setRowHidden(row, not show_row)
            
    def clear_filters(self):
        """清除所有筛选条件"""
        self.studentIdFilter.clear()
        self.dateFilter.reset()  # 使用reset方法清除日期
        self.filter_exams()
        
    def filter_exams(self):
        """根据筛选条件过滤考试记录"""
        student_id = self.studentIdFilter.text().strip().lower()
        selected_date = self.dateFilter.date  # date是属性而不是方法
        
        for row in range(self.examTable.rowCount()):
            show_row = True
            
            # 检查学号筛选条件
            if student_id:
                student_id_item = self.examTable.item(row, 1)  # 学号在第2列
                if not student_id_item or student_id not in student_id_item.text().lower():
                    show_row = False
            
            # 检查日期筛选条件
            if show_row and selected_date:
                start_time_item = self.examTable.item(row, 3)  # 开始时间在第4列
                if start_time_item:
                    exam_date = start_time_item.text().split()[0]  # 只取日期部分
                    if exam_date != selected_date.toString('yyyy-MM-dd'):
                        show_row = False
            
            # 显示或隐藏行
            self.examTable.setRowHidden(row, not show_row)
    
    def refresh_data(self):
        """刷新数据"""
        try:
            self.clear_data()
            self.load_data()
            InfoBar.success(
                title='成功',
                content='数据已刷新',
                parent=self
            ).show()
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=f'刷新数据失败: {str(e)}',
                parent=self
            ).show()
    
    def load_data(self):
        """加载数据"""
        with get_db() as db:
            # 加载用户数据
            users = db.query(User).all()
            total_users = len(users)
            self.userCard.setValue(str(total_users))
            
            for user in users:
                self.userTable.add_user({
                    'student_id': user.student_id,
                    'name': user.name,
                    'bound_ip': user.bound_ip,
                    'bound_time': user.bound_time,
                    'enable_ai': user.enable_ai,
                    'enable_exam': user.enable_exam
                })
            
            # 加载考试数据（包括进行中的考试）并按时间排序
            exams = db.query(Exam).order_by(Exam.start_time.desc()).all()
            total_exams = len(exams)
            self.examCard.setValue(str(total_exams))
            
            # 计算通过率
            if total_exams > 0:
                passed_exams = len([e for e in exams if e.correct_count / e.question_count >= 0.6])
                pass_rate = round(passed_exams / total_exams * 100, 1)
            else:
                pass_rate = 0
            self.passCard.setValue(f"{pass_rate}%")
            
            # 添加考试记录
            for exam in exams:
                user = db.query(User).filter(User.student_id == exam.student_id).first()
                if user:
                    self.examTable.add_exam({
                        'exam_id': exam.exam_id,
                        'student_id': exam.student_id,
                        'student_name': user.name,
                        'start_time': exam.start_time,
                        'submit_time': exam.submit_time,
                        'correct_count': exam.correct_count,
                        'question_count': exam.question_count
                    })
    
    def submit_exam(self, exam_id: str):
        """提交考试"""
        try:
            if submit_exam(exam_id):
                InfoBar.success(
                    title='成功',
                    content='考试已提交',
                    parent=self
                ).show()
                # 刷新数据
                self.refresh_data()
            else:
                InfoBar.error(
                    title='错误',
                    content='提交考试失败',
                    parent=self
                ).show()
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=f'提交考试失败: {str(e)}',
                parent=self
            ).show()
    
    def show_exam_detail(self, exam_id: str):
        """显示考试详情"""
        detail = get_admin_exam_detail(exam_id)
        if detail:
            # 创建详情对话框
            dialog = MessageBoxBase(self)
            dialog.titleLabel = SubtitleLabel('考试详情')
            
            # 基本信息
            content = f"""
学号: {detail['student_id']}
姓名: {detail['student_name']}
开始时间: {detail['start_time'].strftime('%Y-%m-%d %H:%M:%S')}
题目数量: {detail['question_count']}
正确数量: {detail['correct_count']}
得分: {detail['score']}分
            """
            
            # 题目详情
            content += "\n题目详情:\n"
            for i, q in enumerate(detail['questions'], 1):
                content += f"\n{i}. {q['content']}"
                if q['options']:
                    content += "\n选项: " + "\n".join(q['options'])
                content += f"\n正确答案: {q['answer']}"
                content += f"\n学生答案: {q['student_answer']}"
                content += f"\n是否正确: {'✓' if q['is_correct'] else '✗'}"
                if q['explanation']:
                    content += f"\n解释: {q['explanation']}"
                content += "\n"
            
            contentLabel = BodyLabel(content)
            
            # 使用ScrollArea包装内容
            scrollArea = SingleDirectionScrollArea()
            scrollArea.setWidget(contentLabel)
            scrollArea.setMinimumWidth(600)
            scrollArea.setMinimumHeight(400)
            
            dialog.viewLayout.addWidget(dialog.titleLabel)
            dialog.viewLayout.addWidget(scrollArea)
            
            dialog.exec()
