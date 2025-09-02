import os
import stat
from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QWidget, QHBoxLayout, QFileDialog)
from qfluentwidgets import (SubtitleLabel, FluentIcon, PrimaryPushButton, 
                           PushButton, PlainTextEdit, InfoBar, BodyLabel)
from sqlalchemy import create_engine, inspect, text
from models import Base
import logging

class MigrationInterface(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.db_path = None
        self.migrations_to_run = []
        self.setup_ui()

    def setup_ui(self):
        self.vBoxLayout = QVBoxLayout(self)
        
        # Title
        self.titleLabel = SubtitleLabel('数据库迁移工具', self)
        
        # File selection area
        self.fileWidget = QWidget(self)
        self.fileLayout = QHBoxLayout(self.fileWidget)
        self.fileLayout.setContentsMargins(0, 0, 0, 0)
        
        self.selectDbButton = PushButton('选择数据库文件', self)
        self.selectDbButton.setIcon(FluentIcon.DOCUMENT)
        self.dbPathLabel = BodyLabel('未选择文件', self)
        
        self.fileLayout.addWidget(self.selectDbButton)
        self.fileLayout.addWidget(self.dbPathLabel)
        self.fileLayout.addStretch(1)
        
        # Analysis and migration buttons
        self.actionWidget = QWidget(self)
        self.actionLayout = QHBoxLayout(self.actionWidget)
        self.actionLayout.setContentsMargins(0, 0, 0, 0)
        
        self.analyzeButton = PrimaryPushButton('分析数据库', self)
        self.migrateButton = PushButton('执行迁移', self)
        self.migrateButton.setEnabled(False)
        
        self.actionLayout.addWidget(self.analyzeButton)
        self.actionLayout.addWidget(self.migrateButton)
        self.actionLayout.addStretch(1)
        
        # Log viewer
        self.logViewer = PlainTextEdit(self)
        self.logViewer.setReadOnly(True)
        self.logViewer.setPlaceholderText("此处将显示分析结果和迁移日志...")
        
        # Layout
        self.vBoxLayout.addWidget(self.titleLabel)
        self.vBoxLayout.addWidget(self.fileWidget)
        self.vBoxLayout.addWidget(self.actionWidget)
        self.vBoxLayout.addWidget(self.logViewer)
        
        # Connect signals
        self.selectDbButton.clicked.connect(self.select_db_file)
        self.analyzeButton.clicked.connect(self.analyze_database)
        self.migrateButton.clicked.connect(self.run_migration)

    def log(self, message):
        self.logViewer.appendPlainText(message)
        logging.info(message)

    def select_db_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择数据库文件",
            "./data",
            "数据库文件 (*.db)"
        )
        if file_path:
            self.db_path = file_path
            self.dbPathLabel.setText(os.path.basename(file_path))
            self.log(f"已选择数据库: {self.db_path}")
            self.migrateButton.setEnabled(False) # Reselecting file requires re-analysis

    def _fix_db_permissions(self):
        """Ensure the database file and its directory have correct permissions."""
        if not self.db_path:
            return False, "Database path not set."
        try:
            db_dir = os.path.dirname(self.db_path)
            
            # Ensure directory is readable/writable/executable
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, mode=0o755)
            else:
                os.chmod(db_dir, 0o755)
                
            # Ensure the db file itself is writable
            if os.path.exists(self.db_path) and os.path.isfile(self.db_path):
                current_mode = os.stat(self.db_path).st_mode
                # Add write permissions for user and group
                os.chmod(self.db_path, current_mode | stat.S_IWUSR | stat.S_IWGRP)
            self.log(f"已修复文件权限: {self.db_path}")
            return True, None
        except Exception as e:
            self.log(f"修复文件权限失败: {e}")
            return False, str(e)

    def analyze_database(self):
        if not self.db_path:
            InfoBar.warning('提示', '请先选择一个数据库文件', parent=self).show()
            return
        
        # Fix permissions before analysis
        success, error = self._fix_db_permissions()
        if not success:
            InfoBar.error('错误', f'修复文件权限失败: {error}', parent=self).show()
            return

        self.logViewer.clear()
        self.log("开始分析数据库结构...")
        self.migrations_to_run = []
        self.migrateButton.setEnabled(False)
        
        try:
            engine = create_engine(f'sqlite:///{self.db_path}')
            inspector = inspect(engine)
            
            defined_tables = Base.metadata.tables
            existing_tables = inspector.get_table_names()
            
            for table_name, table in defined_tables.items():
                self.log(f"正在检查表: {table_name}")
                if table_name not in existing_tables:
                    self.log(f" -> 发现缺失的表: {table_name}")
                    # This tool will focus on adding columns, not creating tables.
                    # Table creation is handled by Base.metadata.create_all(engine)
                    # We can add a note about it.
                    self.log(f"    (注意: 表创建应由 'init_db' 处理, 此工具主要用于添加缺失的列)")
                    continue

                existing_columns = {col['name'] for col in inspector.get_columns(table_name)}
                
                for column in table.columns:
                    if column.name not in existing_columns:
                        self.log(f" -> 发现缺失的列: {column.name} in {table_name}")
                        # Generate SQL for adding column
                        # This is a simplified version. A full-fledged migration tool would handle types, defaults, etc.
                        col_type = column.type.compile(engine.dialect)
                        sql = f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type}"
                        
                        if column.default is not None:
                            # This is tricky, handle simple cases
                            if isinstance(column.default.arg, (str, bool, int, float)):
                                default_val = column.default.arg
                                if isinstance(default_val, bool):
                                    default_val = 1 if default_val else 0
                                if isinstance(default_val, str):
                                    default_val = f"'{default_val}'"
                                sql += f" DEFAULT {default_val}"

                        self.migrations_to_run.append(sql)
            
            if not self.migrations_to_run:
                self.log("\n分析完成: 数据库结构是最新的，无需迁移。")
                InfoBar.success('成功', '数据库结构是最新的', parent=self).show()
            else:
                self.log("\n分析完成: 检测到需要进行的迁移操作。")
                self.log("待执行的SQL语句:")
                for sql in self.migrations_to_run:
                    self.log(f"  {sql}")
                self.migrateButton.setEnabled(True)
                InfoBar.info('提示', '分析完成，可以执行迁移', parent=self).show()

        except Exception as e:
            self.log(f"分析失败: {e}")
            InfoBar.error('错误', f'分析数据库失败: {e}', parent=self).show()

    def run_migration(self):
        if not self.migrations_to_run:
            InfoBar.warning('提示', '没有需要执行的迁移操作', parent=self).show()
            return

        # Fix permissions before migration
        success, error = self._fix_db_permissions()
        if not success:
            InfoBar.error('错误', f'修复文件权限失败: {error}', parent=self).show()
            return
            
        self.log("\n开始执行数据库迁移...")
        try:
            engine = create_engine(f'sqlite:///{self.db_path}')
            with engine.begin() as connection:
                for sql in self.migrations_to_run:
                    self.log(f"执行: {sql}")
                    connection.execute(text(sql))
            
            self.log("\n迁移成功完成！")
            InfoBar.success('成功', '数据库迁移成功', parent=self).show()
            self.migrations_to_run = []
            self.migrateButton.setEnabled(False)
            
        except Exception as e:
            self.log(f"迁移失败: {e}")
            InfoBar.error('错误', f'数据库迁移失败: {e}', parent=self).show()
