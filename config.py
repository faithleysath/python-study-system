import os
import secrets
import threading
import time
from typing import Optional, Any
import json
from paths import get_base_path

class Config:
    """配置管理类,用于加载和访问yaml配置文件"""
    
    _instance = None
    
    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def _get_config_path(self) -> str:
        """获取配置文件路径"""
        return os.path.join(get_base_path(), 'config.json')
    
    def reload_config(self):
        """重新加载yaml配置文件"""
        config_path = self._get_config_path()
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 加载管理员配置
            admin = config_data.get('admin', {})
            self._admin_username = admin.get('username')
            self._admin_password = admin.get('password')
            
            # DeepSeek配置
            deepseek = config_data.get('deepseek', {})
            self._deepseek_api_key = deepseek.get('api_key', "")
            self._deepseek_base_url = deepseek.get('base_url', "https://api.deepseek.com")
            self._deepseek_model = deepseek.get('model', "deepseek-chat")
            
            # Token配置
            token = config_data.get('token', {})
            self._token_expire_minutes = token.get('expire_minutes', 300)
            
            # 系统业务配置
            system = config_data.get('system', {})
            self._cycle_days = system.get('cycle_days', 7)
            self._correct_threshold = system.get('correct_threshold', 3)
            self._exam_duration = system.get('exam_duration', 30)
            self._exam_question_count = system.get('exam_question_count', 10)
            self._question_range_days = system.get('question_range_days', 7)
            self._pass_score = float(system.get('pass_score', 60))
            self._practice_threshold = system.get('practice_threshold', 10)
            
            # 限流器配置
            rate_limit = config_data.get('rate_limit', {})
            self._rate_limit_max_requests = rate_limit.get('max_requests', 10)
            self._rate_limit_window = rate_limit.get('window', 300)
            
            # 功能开关配置
            features = config_data.get('features', {})
            self._enable_registration = features.get('enable_registration', True)
            self._enable_exam = features.get('enable_exam', True)
            
            # 数据库配置
            database = config_data.get('database', {})
            self._db_file = database.get('file', 'openjudge.db')
            self._db_pool_size = database.get('pool_size', 50)
            self._db_max_overflow = database.get('max_overflow', 100)
            self._db_pool_timeout = database.get('pool_timeout', 60)
            
            if self._practice_threshold < self.exam_question_count:
                raise ValueError("要求刷对的题目数量不能小于抽题数")
                
        except Exception as e:
            print(f"配置加载失败: {e}")
            raise
    
    def start_config_reloader(self):
        """启动配置重载定时器"""
        def reload_loop():
            while True:
                try:
                    self.reload_config()
                except Exception as e:
                    print(f"配置重载失败: {e}")
                time.sleep(1)  # 每秒重载一次
        
        reloader_thread = threading.Thread(target=reload_loop, daemon=True)
        reloader_thread.start()
    
    def __init__(self):
        """初始化配置,只在第一次创建实例时执行"""
        if self._initialized:
            return
            
        # 初始化配置
        self._secret_key = secrets.token_hex(32)
        self.reload_config()
        
        # 启动配置重载器
        self.start_config_reloader()
        
        self._initialized = True

    @property
    def version(self) -> str:
        """获取系统版本"""
        return "1.1.6"
    
    @property
    def detail_info(self) -> str:
        """获取系统详细信息"""
        return "试用版本，仅供学习交流使用" if getattr(self, "_detail_info", None) is None else self._detail_info
    
    @detail_info.setter
    def detail_info(self, value: str):
        """设置系统详细信息"""
        self._detail_info = value
    
    @property
    def admin_username(self) -> Optional[str]:
        """获取管理员用户名"""
        return self._admin_username
    
    @property
    def admin_password(self) -> Optional[str]:
        """获取管理员密码"""
        return self._admin_password
    
    @property
    def secret_key(self) -> Optional[str]:
        """获取密钥"""
        return self._secret_key
    
    @property
    def token_expire_minutes(self) -> int:
        """获取token过期时间(分钟)"""
        return self._token_expire_minutes
    
    @property
    def cycle_days(self) -> int:
        """获取循环周期(天)"""
        return self._cycle_days
    
    @property
    def correct_threshold(self) -> int:
        """获取答对阈值"""
        return self._correct_threshold
    
    @property
    def exam_duration(self) -> int:
        """获取考试时间(分钟)"""
        return self._exam_duration
    
    @property
    def exam_question_count(self) -> int:
        """获取考试题目数量"""
        return self._exam_question_count
    
    @property
    def question_range_days(self) -> int:
        """获取抽题时间范围(天)"""
        return self._question_range_days
    
    @property
    def pass_score(self) -> float:
        """获取考试合格分数线"""
        return self._pass_score
    
    @property
    def practice_threshold(self) -> int:
        """获取参加考试所需的最少练习题数"""
        return self._practice_threshold
    
    @property
    def deepseek_api_key(self) -> Optional[str]:
        """获取DeepSeek API密钥"""
        return self._deepseek_api_key

    @property
    def deepseek_base_url(self) -> str:
        """获取DeepSeek base URL"""
        return self._deepseek_base_url

    @property
    def deepseek_model(self) -> str:
        """获取DeepSeek 模型名称"""
        return self._deepseek_model
        
    @property
    def rate_limit_max_requests(self) -> int:
        """获取限流器最大请求数"""
        return self._rate_limit_max_requests
        
    @property
    def rate_limit_window(self) -> int:
        """获取限流器时间窗口(秒)"""
        return self._rate_limit_window
        
    @property
    def enable_registration(self) -> bool:
        """获取是否允许新用户注册"""
        return self._enable_registration
        
    @property
    def enable_exam(self) -> bool:
        """获取是否允许参加考试"""
        return self._enable_exam
        
    @property
    def db_file(self) -> str:
        """获取数据库文件名"""
        return self._db_file
        
    @property
    def db_pool_size(self) -> int:
        """获取数据库连接池大小"""
        return self._db_pool_size
        
    @property
    def db_max_overflow(self) -> int:
        """获取数据库最大溢出连接数"""
        return self._db_max_overflow
        
    @property
    def db_pool_timeout(self) -> int:
        """获取数据库连接超时时间(秒)"""
        return self._db_pool_timeout
    
    def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """
        通过键名获取配置值
        
        Args:
            key: 配置项的键名，使用.分隔嵌套键，如'database.pool_size'
            default: 默认值,当配置项不存在时返回
            
        Returns:
            配置值或默认值
        """
        try:
            config_path = self._get_config_path()
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 处理嵌套键
            keys = key.split('.')
            value = config_data
            for k in keys:
                value = value[k]
            return value
        except:
            return default

# 创建全局配置实例
config = Config()
