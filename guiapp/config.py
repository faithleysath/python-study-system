from qfluentwidgets import QConfig, ConfigItem, BoolValidator

class Config(QConfig):
    # 管理员配置
    adminUsername = ConfigItem("admin", "username", "admin")
    adminPassword = ConfigItem("admin", "password", "admin123")
    
    # DeepSeek配置
    deepseekApiKey = ConfigItem("deepseek", "api_key", "")
    deepseekBaseUrl = ConfigItem("deepseek", "base_url", "https://api.deepseek.com")
    deepseekModel = ConfigItem("deepseek", "model", "deepseek-chat")
    
    # Token配置
    tokenExpireMinutes = ConfigItem("token", "expire_minutes", 300)
    
    # 系统配置
    systemCycleDays = ConfigItem("system", "cycle_days", 3)
    systemCorrectThreshold = ConfigItem("system", "correct_threshold", 3)
    systemExamDuration = ConfigItem("system", "exam_duration", 10)
    systemExamQuestionCount = ConfigItem("system", "exam_question_count", 10)
    systemQuestionRangeDays = ConfigItem("system", "question_range_days", 3)
    systemPassScore = ConfigItem("system", "pass_score", 60)
    systemPracticeThreshold = ConfigItem("system", "practice_threshold", 20)
    
    # 速率限制配置
    rateLimitMaxRequests = ConfigItem("rate_limit", "max_requests", 5)
    rateLimitWindow = ConfigItem("rate_limit", "window", 120)
    
    # 功能开关配置
    featureEnableRegistration = ConfigItem("features", "enable_registration", False, BoolValidator())
    featureEnableExam = ConfigItem("features", "enable_exam", False, BoolValidator())
    
    # 数据库配置
    databaseFile = ConfigItem("database", "file", "openjudge.db")
    databasePoolSize = ConfigItem("database", "pool_size", 50)
    databaseMaxOverflow = ConfigItem("database", "max_overflow", 100)
    databasePoolTimeout = ConfigItem("database", "pool_timeout", 60)

# 创建全局配置实例
cfg = Config()
