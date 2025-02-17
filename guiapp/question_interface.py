from PyQt5.QtWidgets import (QFrame, QHBoxLayout, QVBoxLayout, QWidget, 
                            QTableWidgetItem, QButtonGroup)
from PyQt5.QtCore import Qt, pyqtSignal
from qfluentwidgets import (SubtitleLabel, FluentIcon, PushButton, InfoBar, BodyLabel, SearchLineEdit,
                           ComboBox, TableWidget, TransparentToolButton,
                           MessageBoxBase, LineEdit, TextEdit,
                           SpinBox, RadioButton, CheckBox, PrimarySplitPushButton,
                           RoundMenu, Action, SwitchButton, TransparentToggleToolButton)

from questions import get_question_by_id, update_question, load_questions

question_types = {
    'single': '单选题',
    'multiple': '多选题',
    'judge': '判断题',
    'blank': '填空题'
}

class QuestionDetailDialog(MessageBoxBase):
    def __init__(self, question_id: str, parent=None):
        super().__init__(parent)
        self.question = get_question_by_id(question_id, include_answer=True)
        self.setup_ui()
        
    def setup_ui(self):
        self.titleLabel = SubtitleLabel('题目详情')
        
        # 基本信息
        self.contentLabel = BodyLabel(f'题目内容：{self.question.content}')
        self.typeLabel = BodyLabel(f'题目类型：{question_types[self.question.type]}')
        self.difficultyLabel = BodyLabel(f'难度等级：{self.question.difficulty}')
        self.tagsLabel = BodyLabel(f'标签：{", ".join(self.question.tags) if hasattr(self.question, "tags") and self.question.tags else "无"}')
        
        # 选择题显示选项
        if hasattr(self.question, 'options') and self.question.options:
            options_text = '\n'.join([f'{i+1}. {opt}' for i, opt in enumerate(self.question.options)])
            self.optionsLabel = BodyLabel(f'选项：\n{options_text}')
        
        # 答案和解释
        self.answerLabel = BodyLabel(f'答案：{self.question.answer}')
        if hasattr(self.question, 'explanation') and self.question.explanation:
            self.explanationLabel = BodyLabel(f'解释：{self.question.explanation}')
        
        # 添加到布局
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addSpacing(16)
        self.viewLayout.addWidget(self.contentLabel)
        self.viewLayout.addWidget(self.typeLabel)
        self.viewLayout.addWidget(self.difficultyLabel)
        self.viewLayout.addWidget(self.tagsLabel)
        
        if hasattr(self, 'optionsLabel'):
            self.viewLayout.addWidget(self.optionsLabel)
            
        self.viewLayout.addWidget(self.answerLabel)
        if hasattr(self, 'explanationLabel'):
            self.viewLayout.addWidget(self.explanationLabel)
            
        # 设置对话框的最小宽度
        self.widget.setMinimumWidth(500)

class OptionsEditDialog(MessageBoxBase):
    def __init__(self, options: list, parent=None):
        super().__init__(parent)
        self.options = options
        self.setup_ui()
        
    def setup_ui(self):
        self.titleLabel = SubtitleLabel('编辑选项')
        
        # 创建四个输入框
        self.optionEdits = []
        for i in range(4):
            label = BodyLabel(chr(65+i), self)
            edit = LineEdit(self)
            # 去掉A. B. C. D.前缀显示实际内容
            if i < len(self.options):
                content = self.options[i]
                if content.startswith(f"{chr(65+i)}. "):
                    content = content[3:]
                edit.setText(content)
            self.optionEdits.append((label, edit))
            
        # 添加到布局
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addSpacing(16)
        
        for label, edit in self.optionEdits:
            self.viewLayout.addWidget(label)
            self.viewLayout.addWidget(edit)
            self.viewLayout.addSpacing(8)
        
        # 设置对话框的最小宽度
        self.widget.setMinimumWidth(400)
    
    def get_options(self) -> list:
        """获取编辑后的选项列表"""
        options = []
        for i, (_, edit) in enumerate(self.optionEdits):
            text = edit.text().strip()
            if text:
                # 添加A. B. C. D.前缀
                options.append(f"{chr(65+i)}. {text}")
        return options

class QuestionEditDialog(MessageBoxBase):
    def __init__(self, question_id: str, parent=None):
        super().__init__(parent)
        self.question = get_question_by_id(question_id, include_answer=True)
        self.setup_ui()
        
    def setup_ui(self):
        self.titleLabel = SubtitleLabel('编辑题目')
        
        # ID（只读）
        self.idLabel = BodyLabel('题目ID:', self)
        self.idEdit = LineEdit(self)
        self.idEdit.setText(self.question.id)
        self.idEdit.setReadOnly(True)
        
        # 启用状态
        self.enabledLabel = BodyLabel('启用状态:', self)
        self.enabledSwitch = SwitchButton(self)
        self.enabledSwitch.setChecked(getattr(self.question, 'enabled', True))
        self.enabledSwitch.setOnText('启用')
        self.enabledSwitch.setOffText('禁用')
        
        # 内容
        self.contentLabel = BodyLabel('题目内容:', self)
        self.contentEdit = TextEdit(self)
        self.contentEdit.setPlainText(self.question.content)
        
        # 类型
        self.typeLabel = BodyLabel('题目类型:', self)
        self.typeComboBox = ComboBox(self)
        self.typeComboBox.addItems(['单选题', '多选题', '判断题', '填空题'])
        self.typeComboBox.setCurrentText(question_types[self.question.type])
        
        # 难度
        self.difficultyLabel = BodyLabel('难度等级:', self)
        self.difficultySpinBox = SpinBox(self)
        self.difficultySpinBox.setRange(1, 3)
        self.difficultySpinBox.setValue(self.question.difficulty)
        
        # 选项编辑按钮（如果有）
        if hasattr(self.question, 'options') and self.question.options:
            self.optionsLabel = BodyLabel('选项:', self)
            self.optionsButton = PushButton('编辑选项', self)
            self.optionsButton.clicked.connect(self.edit_options)
            self.current_options = self.question.options.copy()
        
        # 答案选择
        self.answerLabel = BodyLabel('答案:', self)
        self.answerWidget = QWidget(self)
        self.answerLayout = QHBoxLayout(self.answerWidget)
        
        if self.question.type == 'single':
            # 单选按钮组
            self.buttonGroup = QButtonGroup(self)
            self.answerButtons = []
            for i, opt in enumerate(self.question.options):
                btn = RadioButton(chr(65 + i))
                self.buttonGroup.addButton(btn)
                self.answerLayout.addWidget(btn)
                self.answerButtons.append(btn)
                if chr(65 + i) == str(self.question.answer):
                    btn.setChecked(True)
        elif self.question.type == 'multiple':
            # 复选框组
            self.answerButtons = []
            for i, opt in enumerate(self.question.options):
                btn = CheckBox(chr(65 + i))
                self.answerLayout.addWidget(btn)
                self.answerButtons.append(btn)
                if chr(65 + i) in self.question.answer:
                    btn.setChecked(True)
        else:
            # 其他类型使用文本输入
            self.answerEdit = LineEdit(self)
            self.answerEdit.setText(str(self.question.answer))
            self.answerLayout.addWidget(self.answerEdit)
        
        # 标签
        self.tagsLabel = BodyLabel('标签:', self)
        self.tagsEdit = LineEdit(self)
        if hasattr(self.question, 'tags'):
            self.tagsEdit.setText(', '.join(self.question.tags))
        self.tagsEdit.setPlaceholderText('使用逗号分隔多个标签')
        
        # 解释
        self.explanationLabel = BodyLabel('解释:', self)
        self.explanationEdit = TextEdit(self)
        if self.question.explanation:
            self.explanationEdit.setPlainText(self.question.explanation)
        
        # 添加到布局
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addSpacing(16)
        
        self.viewLayout.addWidget(self.idLabel)
        self.viewLayout.addWidget(self.idEdit)
        self.viewLayout.addSpacing(12)
        
        # 添加启用状态开关
        enabledContainer = QWidget(self)
        enabledLayout = QHBoxLayout(enabledContainer)
        enabledLayout.setContentsMargins(0, 0, 0, 0)
        enabledLayout.addWidget(self.enabledLabel)
        enabledLayout.addWidget(self.enabledSwitch)
        enabledLayout.addStretch(1)
        self.viewLayout.addWidget(enabledContainer)
        self.viewLayout.addSpacing(12)
        
        self.viewLayout.addWidget(self.contentLabel)
        self.viewLayout.addWidget(self.contentEdit)
        self.viewLayout.addSpacing(12)
        
        self.viewLayout.addWidget(self.typeLabel)
        self.viewLayout.addWidget(self.typeComboBox)
        self.viewLayout.addSpacing(12)
        
        self.viewLayout.addWidget(self.difficultyLabel)
        self.viewLayout.addWidget(self.difficultySpinBox)
        self.viewLayout.addSpacing(12)
        
        if hasattr(self, 'optionsLabel'):
            optionsWidget = QWidget(self)
            optionsLayout = QHBoxLayout(optionsWidget)
            optionsLayout.setContentsMargins(0, 0, 0, 0)
            optionsLayout.addWidget(self.optionsLabel)
            optionsLayout.addWidget(self.optionsButton)
            optionsLayout.addStretch(1)
            self.viewLayout.addWidget(optionsWidget)
            self.viewLayout.addSpacing(12)
        
        self.viewLayout.addWidget(self.answerLabel)
        self.viewLayout.addWidget(self.answerWidget)
        self.viewLayout.addSpacing(12)
        
        self.viewLayout.addWidget(self.tagsLabel)
        self.viewLayout.addWidget(self.tagsEdit)
        self.viewLayout.addSpacing(12)
        
        self.viewLayout.addWidget(self.explanationLabel)
        self.viewLayout.addWidget(self.explanationEdit)
        
        # 设置对话框的最小宽度
        self.widget.setMinimumWidth(500)
    
    def edit_options(self):
        """编辑选项"""
        dialog = OptionsEditDialog(self.current_options, self)
        if dialog.exec():
            self.current_options = dialog.get_options()
    
    def get_question_data(self) -> dict:
        """获取编辑后的题目数据"""
        data = {
            'id': self.question.id,
            'content': self.contentEdit.toPlainText(),
            'type': next(k for k, v in question_types.items() if v == self.typeComboBox.currentText()),
            'difficulty': self.difficultySpinBox.value(),
            'explanation': self.explanationEdit.toPlainText() or None,
            'enabled': self.enabledSwitch.isChecked(),
            'tags': [tag.strip() for tag in self.tagsEdit.text().split(',') if tag.strip()]
        }
        
        # 处理选项
        if hasattr(self, 'current_options'):
            data['options'] = self.current_options
            
        # 处理答案
        if data['type'] == 'single':
            for i, btn in enumerate(self.answerButtons):
                if btn.isChecked():
                    data['answer'] = chr(65 + i)
                    break
        elif data['type'] == 'multiple':
            data['answer'] = [chr(65 + i) for i, btn in enumerate(self.answerButtons) if btn.isChecked()]
        elif data['type'] == 'judge':
            data['answer'] = self.answerEdit.text().lower() == 'true'
        else:
            data['answer'] = self.answerEdit.text()
            
        return data

class QuestionTable(TableWidget):
    viewQuestion = pyqtSignal(str)  # 发送题目ID
    editQuestion = pyqtSignal(str)  # 发送题目ID
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels(['ID', '类型', '难度', '内容', '标签', '操作'])

        # 启用排序和多选
        self.setSortingEnabled(True)
        self.setSelectionBehavior(self.SelectRows)
        
        # 设置列宽
        self.setColumnWidth(0, 100)  # ID列
        self.setColumnWidth(1, 100)  # 类型列
        self.setColumnWidth(2, 100)  # 难度列
        self.setColumnWidth(3, 300)  # 内容列
        self.setColumnWidth(4, 150)  # 标签列
        self.setColumnWidth(5, 150)  # 操作列
        
    def add_question(self, question: dict):
        """添加题目到表格"""
        row = self.rowCount()
        self.insertRow(row)
        
        # 添加数据
        for col, value in enumerate([
            question['id'],
            question_types[question['type']],
            str(question['difficulty']),
            question['content'],
            ', '.join(question.get('tags', []))
        ]):
            item = QTableWidgetItem(value)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # 设置为不可编辑
            self.setItem(row, col, item)
        
        # 添加操作按钮
        btnWidget = QWidget()
        layout = QHBoxLayout(btnWidget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 启用状态开关
        enabledBtn = TransparentToggleToolButton(FluentIcon.ACCEPT)
        enabledBtn.setChecked(question.get('enabled', True))
        enabledBtn.setProperty('question_id', question['id'])
        enabledBtn.setToolTip('启用/禁用题目')
        enabledBtn.setIcon(FluentIcon.ACCEPT if question.get('enabled', True) else FluentIcon.CANCEL)
        # 连接信号
        def on_toggled(checked, btn=enabledBtn, qid=question['id']):
            btn.setIcon(FluentIcon.ACCEPT if checked else FluentIcon.CANCEL)
            self.parent().update_question_enabled(qid, checked)
        enabledBtn.toggled.connect(on_toggled)
        layout.addWidget(enabledBtn)
        
        editBtn = TransparentToolButton(FluentIcon.EDIT)
        viewBtn = TransparentToolButton(FluentIcon.VIEW)
        
        # 存储题目ID
        editBtn.setProperty('question_id', question['id'])
        viewBtn.setProperty('question_id', question['id'])
        
        # 连接信号
        editBtn.clicked.connect(lambda: self.editQuestion.emit(question['id']))
        viewBtn.clicked.connect(lambda: self.viewQuestion.emit(question['id']))
        
        layout.addWidget(editBtn)
        layout.addWidget(viewBtn)
        
        self.setCellWidget(row, 5, btnWidget)

class QuestionInterface(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.current_search = ""
        self.current_type_filter = "全部"
        self.current_tag_filter = "全部标签"
        self.all_tags = set()  # 存储所有标签
        self.setup_ui()
        self.load_questions()
        
        # 连接信号
        self.table.viewQuestion.connect(self.show_question_detail)
        self.table.editQuestion.connect(self.edit_question)
        
    def show_question_detail(self, question_id: str):
        """显示题目详情对话框"""
        dialog = QuestionDetailDialog(question_id, self)
        dialog.exec()
        
    def update_question_enabled(self, question_id: str, enabled: bool):
        """更新题目启用状态"""
        try:
            question = get_question_by_id(question_id, include_answer=True)
            question_data = question.model_dump()
            question_data['enabled'] = enabled
            update_question(question_id, question_data)
            
            InfoBar.success(
                title='成功',
                content=f'已{"启用" if enabled else "禁用"}题目 {question_id}',
                parent=self
            ).show()
            
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=f'更新题目状态失败: {str(e)}',
                parent=self
            ).show()
    
    def edit_question(self, question_id: str):
        """编辑题目"""
        dialog = QuestionEditDialog(question_id, self)
        if dialog.exec():
            try:
                # 获取编辑后的数据
                question_data = dialog.get_question_data()
                
                # 使用questions.py中的函数更新题目
                update_question(question_id, question_data)
                
                # 刷新表格
                self.table.clearContents()
                self.table.setRowCount(0)
                self.load_questions()
                
                InfoBar.success(
                    title='成功',
                    content='题目已更新',
                    parent=self
                ).show()
                
            except Exception as e:
                InfoBar.error(
                    title='错误',
                    content=f'保存题目失败: {str(e)}',
                    parent=self
                ).show()
        
    def setup_ui(self):
        self.vBoxLayout = QVBoxLayout(self)
        
        # 工具栏
        self.toolWidget = QWidget(self)
        self.toolLayout = QHBoxLayout(self.toolWidget)
        
        self.searchBox = SearchLineEdit(self)
        self.searchBox.setPlaceholderText('搜索题目...')
        self.searchBox.searchSignal.connect(self.search_questions)
        self.searchBox.textChanged.connect(self.search_questions)
        
        self.typeFilter = ComboBox(self)
        self.typeFilter.addItems(['全部', '单选题', '多选题', '判断题', '填空题'])
        self.typeFilter.currentTextChanged.connect(self.filter_questions)
        
        # 创建题型选择下拉框
        self.typeComboBox = ComboBox(self)
        self.typeComboBox.setPlaceholderText("选择题目类型")
        for type_key, type_name in question_types.items():
            self.typeComboBox.addItem(type_name, userData=type_key)
        self.typeComboBox.setCurrentIndex(-1)  # 默认不选中
        
        # 创建PrimarySplitPushButton
        self.addButton = PrimarySplitPushButton('添加题目', self)
        self.addButton.clicked.connect(self.create_empty_question)
        self.addButton.setEnabled(False)  # 默认禁用
        
        # 创建菜单
        menu = RoundMenu(parent=self.addButton)
        menu.addAction(Action(FluentIcon.ROBOT, 'AI导入', triggered=self.ai_import_questions))
        menu.addAction(Action(FluentIcon.ROBOT, 'AI批量导入', triggered=self.ai_batch_import_questions))
        
        # 添加菜单到按钮
        self.addButton.setFlyout(menu)
        
        # 连接信号
        self.typeComboBox.currentIndexChanged.connect(self.on_type_changed)
        
        self.toolLayout.addWidget(self.searchBox)
        self.toolLayout.addWidget(self.typeFilter)
        
        # 添加标签筛选
        self.tagFilter = ComboBox(self)
        self.tagFilter.addItem('全部标签')
        self.tagFilter.currentTextChanged.connect(self.filter_by_tag)
        self.toolLayout.addWidget(self.tagFilter)
        
        self.toolLayout.addStretch(1)
        
        # 添加批量操作按钮
        self.batchButton = PrimarySplitPushButton('批量操作', self)
        menu = RoundMenu(parent=self.batchButton)
        menu.addAction(Action(FluentIcon.ACCEPT, '批量启用', triggered=lambda: self.batch_enable(True)))
        menu.addAction(Action(FluentIcon.CANCEL, '批量禁用', triggered=lambda: self.batch_enable(False)))
        menu.addAction(Action(FluentIcon.DELETE, '批量删除', triggered=self.batch_delete))
        menu.addAction(Action(FluentIcon.TAG, '批量添加标签', triggered=self.batch_add_tag))
        menu.addAction(Action(FluentIcon.REMOVE_FROM, '批量删除标签', triggered=self.batch_remove_tag))
        self.batchButton.setFlyout(menu)
        
        self.toolLayout.addWidget(self.batchButton)
        self.toolLayout.addWidget(self.typeComboBox)
        self.toolLayout.addWidget(self.addButton)
        
        # 题目表格
        self.table = QuestionTable(self)
        
        self.vBoxLayout.addWidget(self.toolWidget)
        self.vBoxLayout.addWidget(self.table)
        
    def load_questions(self):
        """加载题目到表格"""
        try:
            questions = load_questions()
            
            # 收集所有标签
            self.all_tags.clear()
            for q in questions:
                if hasattr(q, 'tags'):
                    self.all_tags.update(q.tags)
            
            # 更新标签筛选下拉框
            current_tag = self.tagFilter.currentText()
            self.tagFilter.clear()
            self.tagFilter.addItem('全部标签')
            self.tagFilter.addItems(sorted(self.all_tags))
            if current_tag in self.all_tags:
                self.tagFilter.setCurrentText(current_tag)
            
            # 添加题目到表格
            for q in questions:
                self.table.add_question(q.model_dump())
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=f'加载题目失败: {str(e)}',
                parent=self
            ).show()
            
    def update_table_visibility(self):
        """统一处理搜索和过滤的逻辑"""
        for row in range(self.table.rowCount()):
            # 首先检查是否符合搜索条件
            show = False
            if not self.current_search.strip():
                show = True
            else:
                for col in range(self.table.columnCount() - 1):  # 不搜索操作列
                    item = self.table.item(row, col)
                    if item and self.current_search.lower() in item.text().lower():
                        show = True
                        break
            
            # 如果符合搜索条件,再检查是否符合类型过滤条件
            if show and self.current_type_filter != '全部':
                type_item = self.table.item(row, 1)
                show = type_item.text() == self.current_type_filter
            
            # 如果符合类型过滤条件,再检查是否符合标签过滤条件
            if show and self.current_tag_filter != '全部标签':
                tags_item = self.table.item(row, 4)
                show = self.current_tag_filter in tags_item.text().split(', ')
            
            self.table.setRowHidden(row, not show)
    
    def search_questions(self, keyword: str):
        """搜索题目"""
        self.current_search = keyword
        self.update_table_visibility()
            
    def filter_questions(self, type_text: str):
        """按类型筛选题目"""
        self.current_type_filter = type_text
        self.update_table_visibility()
        
    def filter_by_tag(self, tag_text: str):
        """按标签筛选题目"""
        self.current_tag_filter = tag_text
        self.update_table_visibility()
        
    def batch_enable(self, enable: bool):
        """批量启用/禁用题目"""
        try:
            count = 0
            selected_rows = set(item.row() for item in self.table.selectedItems())
            
            if not selected_rows:
                InfoBar.warning(
                    title='提示',
                    content='请先选择要操作的题目',
                    parent=self
                ).show()
                return
            
            for row in selected_rows:
                if not self.table.isRowHidden(row):
                    # 获取题目ID
                    id_item = self.table.item(row, 0)
                    if id_item:
                        question_id = id_item.text()
                        question = get_question_by_id(question_id, include_answer=True)
                        question_data = question.model_dump()
                        if question_data['enabled'] != enable:
                            question_data['enabled'] = enable
                            update_question(question_id, question_data)
                            count += 1
            
            # 刷新表格
            self.table.clearContents()
            self.table.setRowCount(0)
            self.load_questions()
            
            InfoBar.success(
                title='成功',
                content=f'已{"启用" if enable else "禁用"} {count} 道题目',
                parent=self
            ).show()
            
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=f'批量{"启用" if enable else "禁用"}失败: {str(e)}',
                parent=self
            ).show()
            
    def batch_delete(self):
        """批量删除题目"""
        try:
            selected_rows = set(item.row() for item in self.table.selectedItems())
            
            if not selected_rows:
                InfoBar.warning(
                    title='提示',
                    content='请先选择要删除的题目',
                    parent=self
                ).show()
                return
            
            # 创建确认对话框
            dialog = MessageBoxBase(self)
            dialog.titleLabel = SubtitleLabel('确认删除')
            dialog.contentLabel = BodyLabel(f'确定要删除选中的 {len(selected_rows)} 道题目吗？此操作不可恢复。')
            
            if dialog.exec():
                count = 0
                for row in selected_rows:
                    if not self.table.isRowHidden(row):
                        # 获取题目ID
                        id_item = self.table.item(row, 0)
                        if id_item:
                            question_id = id_item.text()
                            # 从questions.json中删除题目
                            try:
                                with open('data/questions.json', 'r', encoding='utf-8') as f:
                                    questions = json.load(f)
                                questions = [q for q in questions if q['id'] != question_id]
                                with open('data/questions.json', 'w', encoding='utf-8') as f:
                                    json.dump(questions, f, ensure_ascii=False, indent=2)
                                count += 1
                            except Exception as e:
                                InfoBar.error(
                                    title='错误',
                                    content=f'删除题目 {question_id} 失败: {str(e)}',
                                    parent=self
                                ).show()
                
                # 刷新表格
                self.table.clearContents()
                self.table.setRowCount(0)
                self.load_questions()
                
                InfoBar.success(
                    title='成功',
                    content=f'已删除 {count} 道题目',
                    parent=self
                ).show()
            
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=f'批量删除失败: {str(e)}',
                parent=self
            ).show()
            
    def batch_add_tag(self):
        """批量添加标签"""
        try:
            selected_rows = set(item.row() for item in self.table.selectedItems())
            
            if not selected_rows:
                InfoBar.warning(
                    title='提示',
                    content='请先选择要添加标签的题目',
                    parent=self
                ).show()
                return
            
            # 创建输入对话框
            dialog = MessageBoxBase(self)
            dialog.titleLabel = SubtitleLabel('添加标签')
            dialog.contentLabel = BodyLabel('请输入要添加的标签（多个标签用逗号分隔）:')
            
            # 添加输入框
            dialog.tagEdit = LineEdit(dialog)
            dialog.tagEdit.setPlaceholderText('例如: 简单,Python,面向对象')
            dialog.viewLayout.addWidget(dialog.tagEdit)
            
            if dialog.exec():
                new_tags = [tag.strip() for tag in dialog.tagEdit.text().split(',') if tag.strip()]
                if not new_tags:
                    InfoBar.warning(
                        title='提示',
                        content='请输入有效的标签',
                        parent=self
                    ).show()
                    return
                
                count = 0
                for row in selected_rows:
                    if not self.table.isRowHidden(row):
                        # 获取题目ID
                        id_item = self.table.item(row, 0)
                        if id_item:
                            question_id = id_item.text()
                            question = get_question_by_id(question_id, include_answer=True)
                            question_data = question.model_dump()
                            
                            # 添加新标签
                            current_tags = set(question_data.get('tags', []))
                            current_tags.update(new_tags)
                            question_data['tags'] = sorted(list(current_tags))
                            
                            # 更新题目
                            update_question(question_id, question_data)
                            count += 1
                
                # 刷新表格
                self.table.clearContents()
                self.table.setRowCount(0)
                self.load_questions()
                
                InfoBar.success(
                    title='成功',
                    content=f'已为 {count} 道题目添加标签',
                    parent=self
                ).show()
            
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=f'批量添加标签失败: {str(e)}',
                parent=self
            ).show()
            
    def batch_remove_tag(self):
        """批量删除标签"""
        try:
            selected_rows = set(item.row() for item in self.table.selectedItems())
            
            if not selected_rows:
                InfoBar.warning(
                    title='提示',
                    content='请先选择要删除标签的题目',
                    parent=self
                ).show()
                return
            
            # 收集选中题目的所有标签
            available_tags = set()
            for row in selected_rows:
                if not self.table.isRowHidden(row):
                    tags_item = self.table.item(row, 4)
                    if tags_item:
                        tags = [tag.strip() for tag in tags_item.text().split(',') if tag.strip()]
                        available_tags.update(tags)
            
            if not available_tags:
                InfoBar.warning(
                    title='提示',
                    content='选中的题目没有标签可以删除',
                    parent=self
                ).show()
                return
            
            # 创建标签选择对话框
            dialog = MessageBoxBase(self)
            dialog.titleLabel = SubtitleLabel('删除标签')
            dialog.contentLabel = BodyLabel('请选择要删除的标签:')
            
            # 添加标签复选框
            dialog.tagCheckBoxes = []
            for tag in sorted(available_tags):
                checkbox = CheckBox(tag, dialog)
                dialog.tagCheckBoxes.append(checkbox)
                dialog.viewLayout.addWidget(checkbox)
            
            if dialog.exec():
                # 获取选中的标签
                tags_to_remove = [cb.text() for cb in dialog.tagCheckBoxes if cb.isChecked()]
                if not tags_to_remove:
                    InfoBar.warning(
                        title='提示',
                        content='请选择要删除的标签',
                        parent=self
                    ).show()
                    return
                
                count = 0
                for row in selected_rows:
                    if not self.table.isRowHidden(row):
                        # 获取题目ID
                        id_item = self.table.item(row, 0)
                        if id_item:
                            question_id = id_item.text()
                            question = get_question_by_id(question_id, include_answer=True)
                            question_data = question.model_dump()
                            
                            # 删除选中的标签
                            current_tags = set(question_data.get('tags', []))
                            current_tags.difference_update(tags_to_remove)
                            question_data['tags'] = sorted(list(current_tags))
                            
                            # 更新题目
                            update_question(question_id, question_data)
                            count += 1
                
                # 刷新表格
                self.table.clearContents()
                self.table.setRowCount(0)
                self.load_questions()
                
                InfoBar.success(
                    title='成功',
                    content=f'已为 {count} 道题目删除选中的标签',
                    parent=self
                ).show()
            
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=f'批量删除标签失败: {str(e)}',
                parent=self
            ).show()
                
    def on_type_changed(self, index):
        """题型选择改变时的处理"""
        self.addButton.setEnabled(index >= 0)
    
    def create_empty_question(self):
        """创建一个空的题目"""
        try:
            # 获取选中的题型
            question_type = self.typeComboBox.currentData()
            if not question_type:
                return
            
            # 加载现有题目获取最大ID
            questions = load_questions()
            if questions:
                max_id = max(int(q.id[1:]) for q in questions)
                new_id = f"q{str(max_id + 1).zfill(3)}"
            else:
                # 题库为空时从q001开始
                new_id = "q001"
            
            # 创建空题目
            empty_question = {
                'id': new_id,
                'type': question_type,
                'difficulty': 1,
                'content': '',
                'explanation': None,
                'tags': []
            }
            
            # 根据题型添加特定字段
            if question_type in ['single', 'multiple']:
                empty_question['options'] = [
                    'A. ',
                    'B. ',
                    'C. ',
                    'D. '
                ]
                empty_question['answer'] = 'A' if question_type == 'single' else ['A']
            elif question_type == 'judge':
                empty_question['answer'] = True
            else:  # blank
                empty_question['answer'] = ''
            
            # 保存题目
            update_question(new_id, empty_question)
            
            # 刷新表格
            self.table.clearContents()
            self.table.setRowCount(0)
            self.load_questions()
            
            InfoBar.success(
                title='成功',
                content='已创建新题目',
                parent=self
            ).show()

            # 自动打开编辑对话框
            self.edit_question(new_id)
            
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=f'创建题目失败: {str(e)}',
                parent=self
            ).show()
            
    def ai_import_questions(self):
        """AI导入题目"""
        dialog = AIImportDialog(self)
        if dialog.exec():
            try:
                # 获取AI生成的题目数据
                question_data = dialog.import_question()
                
                # 加载现有题目获取最大ID
                questions = load_questions()
                if questions:
                    max_id = max(int(q.id[1:]) for q in questions)
                else:
                    # 题库为空时从q001开始
                    max_id = 0
                new_id = f"q{str(max_id + 1).zfill(3)}"
                
                # 添加其他必要字段
                question_data['id'] = new_id
                question_data['enabled'] = False
                question_data['is_ai'] = True
                question_data['tags'] = []
                
                # 保存题目
                update_question(new_id, question_data)
                
                # 刷新表格
                self.table.clearContents()
                self.table.setRowCount(0)
                self.load_questions()
                
                InfoBar.success(
                    title='成功',
                    content='已导入新题目',
                    parent=self
                ).show()
                
            except Exception as e:
                InfoBar.error(
                    title='错误',
                    content=f'导入题目失败: {str(e)}',
                    parent=self
                ).show()
    
    def ai_batch_import_questions(self):
        """AI批量导入题目"""
        dialog = AIBatchImportDialog(self)
        if dialog.exec():
            try:
                # 获取AI生成的题目数据列表
                questions_data = dialog.import_questions()
                
                # 加载现有题目获取最大ID
                questions = load_questions()
                if questions:
                    max_id = max(int(q.id[1:]) for q in questions)
                else:
                    # 题库为空时从q001开始
                    max_id = 0
                
                # 批量导入题目
                success_count = 0
                for i, question_data in enumerate(questions_data, 1):
                    try:
                        new_id = f"q{str(max_id + i).zfill(3)}"
                        
                        # 添加其他必要字段
                        question_data['id'] = new_id
                        question_data['enabled'] = False
                        question_data['is_ai'] = True
                        question_data['tags'] = []
                        
                        # 保存题目
                        update_question(new_id, question_data)
                        success_count += 1
                        
                    except Exception as e:
                        InfoBar.error(
                            title='错误',
                            content=f'导入第 {i} 道题目失败: {str(e)}',
                            parent=self
                        ).show()
                
                # 刷新表格
                self.table.clearContents()
                self.table.setRowCount(0)
                self.load_questions()
                
                InfoBar.success(
                    title='成功',
                    content=f'已导入 {success_count} 道新题目',
                    parent=self
                ).show()
                
            except Exception as e:
                InfoBar.error(
                    title='错误',
                    content=f'批量导入失败: {str(e)}',
                    parent=self
                ).show()
    
from PyQt5.QtCore import QThread, pyqtSignal
import json
from openai import OpenAI
from .config import cfg

class AIGenerateThread(QThread):
    """AI生成题目的后台线程"""
    finished = pyqtSignal(object)  # 生成成功信号，可以是dict或list[dict]
    error = pyqtSignal(str)      # 错误信号
    
    def __init__(self, text, is_batch=False):
        super().__init__()
        self.text = text
        self.is_batch = is_batch
        
    def run(self):
        try:
            # 获取API密钥
            api_key = cfg.deepseekApiKey.value
            if not api_key:
                raise ValueError("请先在设置中配置DeepSeek API密钥")
            
            # 创建OpenAI客户端
            client = OpenAI(
                api_key=api_key,
                base_url=cfg.deepseekBaseUrl.value
            )
            
            # 系统提示词
            if self.is_batch:
                system_prompt = """
                你是一个专业的题目解析助手。用户会提供一段文本，其中包含多道题目。请将这些题目解析为以下格式的JSON：

                {
                    "questions": [
                        {
                            "type": "类型",  // 必须是以下之一: "single", "multiple", "judge", "blank"
                            "content": "题目内容",  // 必填
                            "options": [  // 仅选择题(single/multiple)必填，其他类型不需要
                                "A. 选项1",  // 必须以A. B. C. D.开头
                                "B. 选项2",
                                "C. 选项3",
                                "D. 选项4"
                            ],
                            "answer": "答案",  // 根据题型格式不同：
                                             // single: "A"到"D"的字母
                                             // multiple: ["A","B"]等字母数组
                                             // judge: true/false
                                             // blank: 答案文本
                            "explanation": "解释",  // 必填
                            "difficulty": 难度数字  // 必填，1=简单，2=中等，3=困难
                        }
                        // ... 更多题目
                    ]
                }

                注意事项：
                1. 必须严格按照上述JSON格式返回，保持字段名称完全一致
                2. questions必须是数组，即使只有一道题目
                3. 每个字段都必须提供，不能缺少
                4. difficulty必须是1-3的整数
                5. 选择题的选项必须以A. B. C. D.开头
                """
            else:
                system_prompt = """
                你是一个专业的题目解析助手。请将用户提供的题目文本解析为以下格式的JSON：

                {
                    "questions": [
                        {
                            "type": "类型",  // 必须是以下之一: "single", "multiple", "judge", "blank"
                            "content": "题目内容",  // 必填
                            "options": [  // 仅选择题(single/multiple)必填，其他类型不需要
                                "A. 选项1",  // 必须以A. B. C. D.开头
                                "B. 选项2",
                                "C. 选项3",
                                "D. 选项4"
                            ],
                            "answer": "答案",  // 根据题型格式不同：
                                             // single: "A"到"D"的字母
                                             // multiple: ["A","B"]等字母数组
                                             // judge: true/false
                                             // blank: 答案文本
                            "explanation": "解释",  // 必填
                            "difficulty": 难度数字  // 必填，1=简单，2=中等，3=困难
                        }
                    ]
                }

                注意事项：
                1. 必须严格按照上述JSON格式返回，保持字段名称完全一致
                2. questions数组中只需要包含一个题目对象
                3. 每个字段都必须提供，不能缺少
                4. difficulty必须是1-3的整数
                5. 选择题的选项必须以A. B. C. D.开头
                """
            
            # 发送请求
            response = client.chat.completions.create(
                model=cfg.deepseekModel.value,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": self.text}
                ],
                response_format={
                    'type': 'json_object'
                }
            )
            
            # 解析返回的JSON
            raw_content = response.choices[0].message.content
            
            result = json.loads(raw_content)
            
            # 提取题目数据
            if 'questions' in result:
                result = result['questions']
            
            # 如果是批量导入模式，确保结果是列表
            if self.is_batch:
                if not isinstance(result, list):
                    # 如果返回的是单个题目的字典，将其转换为列表
                    if isinstance(result, dict):
                        result = [result]
                    else:
                        raise ValueError("AI返回的数据格式不正确，应为题目列表")
            else:
                # 单题模式，确保结果是字典
                if isinstance(result, list):
                    if len(result) > 0:
                        result = result[0]
                    else:
                        raise ValueError("AI未返回题目数据")
                elif not isinstance(result, dict):
                    raise ValueError("AI返回的数据格式不正确，应为题目对象")
            
            self.finished.emit(result)
            
        except Exception as e:
            self.error.emit(str(e))

class AIBatchImportDialog(MessageBoxBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.question_data = None
        self.is_preview_mode = False
        
    def setup_ui(self):
        self.titleLabel = SubtitleLabel('AI批量导入题目')
        
        # 创建模式标签
        self.modeLabel = BodyLabel("请输入题目文本（每道题之间用空行分隔）:", self)
        
        # 创建文本输入框
        self.textEdit = TextEdit(self)
        self.textEdit.setPlaceholderText("请输入多道题目，任意格式均可，只要人能理解，ai就能理解。甚至只用输入题面和选项，ai就能自动生成答案和解析。")
        self.textEdit.setMinimumHeight(400)
        
        # 添加生成按钮
        self.generateButton = PushButton('批量生成题目', self)
        self.generateButton.clicked.connect(self.generate_questions)
        
        # 添加重新编辑按钮（初始隐藏）
        self.editButton = PushButton('重新编辑', self)
        self.editButton.clicked.connect(self.switch_to_edit_mode)
        self.editButton.hide()
        
        # 添加到布局
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addSpacing(16)
        self.viewLayout.addWidget(self.modeLabel)
        self.viewLayout.addWidget(self.textEdit)
        
        # 创建按钮容器
        buttonContainer = QWidget(self)
        buttonLayout = QHBoxLayout(buttonContainer)
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addWidget(self.generateButton)
        buttonLayout.addWidget(self.editButton)
        
        self.viewLayout.addWidget(buttonContainer)
        
        # 设置对话框的最小宽度
        self.widget.setMinimumWidth(600)
        
        # 禁用确定按钮，直到生成成功
        self.yesButton.setEnabled(False)
    
    def get_text(self) -> str:
        """获取输入的文本"""
        return self.textEdit.toPlainText().strip()
    
    def switch_to_preview_mode(self, questions: list):
        """切换到预览模式"""
        self.is_preview_mode = True
        self.modeLabel.setText(f"题目预览（共 {len(questions)} 道题）:")
        self.textEdit.setReadOnly(True)
        
        # 创建预览内容
        content = []
        for i, q in enumerate(questions, 1):
            content.append(f"第 {i} 题:\n")
            content.append(f"题目类型：{question_types.get(q.get('type', ''), '未知类型')}")
            content.append(f"难度等级：{q.get('difficulty', 1)}")  # 默认难度为1
            content.append(f"题目内容：{q.get('content', '未知内容')}")
            
            if q.get('options'):
                content.append("选项：")
                content.extend(q['options'])
                
            content.append(f"答案：{q.get('answer', '未设置')}")
            content.append(f"解释：{q.get('explanation', '无')}")
            content.append("\n" + "="*50 + "\n")
        
        self.textEdit.setPlainText("\n".join(content))
        
        # 更新按钮状态
        self.generateButton.hide()
        self.editButton.show()
        self.yesButton.setEnabled(True)
        
    def switch_to_edit_mode(self):
        """切换到编辑模式"""
        self.is_preview_mode = False
        self.modeLabel.setText("请输入题目文本（每道题之间用空行分隔）:")
        self.textEdit.setReadOnly(False)
        self.textEdit.clear()
        self.textEdit.setPlaceholderText("请输入多道题目，任意格式均可，只要人能理解，ai就能理解。甚至只用输入题面和选项，ai就能自动生成答案和解析。")
        
        # 更新按钮状态
        self.generateButton.show()
        self.editButton.hide()
        self.yesButton.setEnabled(False)
        self.question_data = None
    
    def generate_questions(self):
        """生成题目"""
        text = self.get_text()
        if not text:
            InfoBar.error(
                title='错误',
                content='请输入题目文本',
                parent=self
            ).show()
            return
        
        # 禁用生成按钮
        self.generateButton.setEnabled(False)
        self.generateButton.setText('生成中...')
        
        # 创建并启动生成线程
        self.thread = AIGenerateThread(text, is_batch=True)
        self.thread.finished.connect(self.on_generation_finished)
        self.thread.error.connect(self.on_generation_error)
        self.thread.start()
    
    def on_generation_finished(self, result: list):
        """生成完成的处理"""
        self.generateButton.setEnabled(True)
        self.generateButton.setText('批量生成题目')
        
        # 保存结果并切换到预览模式
        self.question_data = result
        self.switch_to_preview_mode(result)
        
        InfoBar.success(
            title='成功',
            content=f'已生成 {len(result)} 道题目，请确认预览内容',
            parent=self
        ).show()
    
    def on_generation_error(self, error: str):
        """生成错误的处理"""
        self.generateButton.setEnabled(True)
        self.generateButton.setText('批量生成题目')
        InfoBar.error(
            title='错误',
            content=f'生成题目失败: {error}',
            parent=self
        ).show()
    
    def import_questions(self) -> list:
        """返回生成的题目数据列表"""
        return self.question_data

class AIImportDialog(MessageBoxBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.question_data = None
        self.is_preview_mode = False
        
    def setup_ui(self):
        self.titleLabel = SubtitleLabel('AI导入题目')
        
        # 创建模式标签
        self.modeLabel = BodyLabel("请输入题目文本:", self)
        
        # 创建文本输入框
        self.textEdit = TextEdit(self)
        self.textEdit.setPlaceholderText("请输入题目，任意格式均可，只要人能理解，ai就能理解。甚至只用输入题面和选项，ai就能自动生成答案和解析。")
        self.textEdit.setMinimumHeight(300)
        
        # 添加生成按钮
        self.generateButton = PushButton('生成题目', self)
        self.generateButton.clicked.connect(self.generate_question)
        
        # 添加重新编辑按钮（初始隐藏）
        self.editButton = PushButton('重新编辑', self)
        self.editButton.clicked.connect(self.switch_to_edit_mode)
        self.editButton.hide()
        
        # 添加到布局
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addSpacing(16)
        self.viewLayout.addWidget(self.modeLabel)
        self.viewLayout.addWidget(self.textEdit)
        
        # 创建按钮容器
        buttonContainer = QWidget(self)
        buttonLayout = QHBoxLayout(buttonContainer)
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        buttonLayout.addWidget(self.generateButton)
        buttonLayout.addWidget(self.editButton)
        
        self.viewLayout.addWidget(buttonContainer)
        
        # 设置对话框的最小宽度
        self.widget.setMinimumWidth(500)
        
        # 禁用确定按钮，直到生成成功
        self.yesButton.setEnabled(False)
    
    def get_text(self) -> str:
        """获取输入的文本"""
        return self.textEdit.toPlainText().strip()
    
    def switch_to_preview_mode(self, question_data: dict):
        """切换到预览模式"""
        self.is_preview_mode = True
        self.modeLabel.setText("题目预览:")
        self.textEdit.setReadOnly(True)
        
        # 创建预览内容
        content = f"题目类型：{question_types[question_data['type']]}\n\n"
        content += f"难度等级：{question_data['difficulty']}\n\n"
        content += f"题目内容：{question_data['content']}\n\n"
        
        if 'options' in question_data:
            content += "选项：\n" + "\n".join(question_data['options']) + "\n\n"
            
        content += f"答案：{question_data['answer']}\n\n"
        content += f"解释：{question_data['explanation']}"
        
        self.textEdit.setPlainText(content)
        
        # 更新按钮状态
        self.generateButton.hide()
        self.editButton.show()
        self.yesButton.setEnabled(True)
        
    def switch_to_edit_mode(self):
        """切换到编辑模式"""
        self.is_preview_mode = False
        self.modeLabel.setText("请输入题目文本:")
        self.textEdit.setReadOnly(False)
        self.textEdit.clear()
        self.textEdit.setPlaceholderText("请输入题目，任意格式均可，只要人能理解，ai就能理解。甚至只用输入题面和选项，ai就能自动生成答案和解析。")
        
        # 更新按钮状态
        self.generateButton.show()
        self.editButton.hide()
        self.yesButton.setEnabled(False)
        self.question_data = None
    
    def generate_question(self):
        """生成题目"""
        text = self.get_text()
        if not text:
            InfoBar.error(
                title='错误',
                content='请输入题目文本',
                parent=self
            ).show()
            return
        
        # 禁用生成按钮
        self.generateButton.setEnabled(False)
        self.generateButton.setText('生成中...')
        
        # 创建并启动生成线程
        self.thread = AIGenerateThread(text)
        self.thread.finished.connect(self.on_generation_finished)
        self.thread.error.connect(self.on_generation_error)
        self.thread.start()
    
    def on_generation_finished(self, result: dict):
        """生成完成的处理"""
        self.generateButton.setEnabled(True)
        self.generateButton.setText('生成题目')
        
        # 保存结果并切换到预览模式
        self.question_data = result
        self.switch_to_preview_mode(result)
        
        InfoBar.success(
            title='成功',
            content='题目已生成，请确认预览内容',
            parent=self
        ).show()
    
    def on_generation_error(self, error: str):
        """生成错误的处理"""
        self.generateButton.setEnabled(True)
        self.generateButton.setText('生成题目')
        InfoBar.error(
            title='错误',
            content=f'生成题目失败: {error}',
            parent=self
        ).show()
    
    def import_question(self) -> dict:
        """返回生成的题目数据"""
        return self.question_data
