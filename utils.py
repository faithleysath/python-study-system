import time
from collections import defaultdict

def get_client_ip(request) -> str:
    """获取客户端真实IP地址
    
    按优先级依次检查各种HTTP头部来确定客户端真实IP地址
    支持多种代理头部和CDN服务商
    """
    # 按优先级顺序检查的头部列表
    HEADERS_TO_CHECK = [
        'CF-Connecting-IP',      # Cloudflare
        'True-Client-IP',        # Akamai
        'X-Real-IP',            # Nginx代理
        'X-Original-Forwarded-For',
        'X-Forwarded-For'
    ]
    
    # 依次检查各个头部
    for header in HEADERS_TO_CHECK:
        if header.lower() in request.headers:
            ip = request.headers[header]
            if ',' in ip:  # 如果包含多个IP,取第一个
                ip = ip.split(',')[0].strip()
            if ip and _is_valid_ip(ip):
                return ip
                
    # 如果没有找到有效的代理IP,返回直连IP
    return request.client.host if request.client else "0.0.0.0"

def _is_valid_ip(ip: str) -> bool:
    """验证IP地址是否有效"""
    try:
        # 简单的IPv4地址验证
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        return all(0 <= int(part) <= 255 for part in parts)
    except (AttributeError, TypeError, ValueError):
        return False

# 限流器实现
class RateLimiter:
    def __init__(self, max_requests: int, time_window: int):
        """
        初始化限流器
        
        Args:
            max_requests: 时间窗口内允许的最大请求数
            time_window: 时间窗口大小(秒)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = defaultdict(list)  # student_id -> [timestamp1, timestamp2, ...]
    
    def is_allowed(self, student_id: str) -> bool:
        """
        检查请求是否被允许
        
        Args:
            student_id: 学生ID
            
        Returns:
            bool: 是否允许请求
        """
        now = time.time()
        
        # 清理过期的请求记录
        self.requests[student_id] = [
            ts for ts in self.requests[student_id]
            if now - ts < self.time_window
        ]
        
        # 检查是否超过限制
        if len(self.requests[student_id]) >= self.max_requests:
            return False
        
        # 记录新的请求
        self.requests[student_id].append(now)
        return True
    
    def get_remaining_time(self, student_id: str) -> float:
        """
        获取需要等待的时间(秒)
        
        Args:
            student_id: 学生ID
            
        Returns:
            float: 需要等待的秒数
        """
        if not self.requests[student_id]:
            return 0
            
        now = time.time()
        oldest_request = self.requests[student_id][0]
        time_passed = now - oldest_request
        
        if time_passed >= self.time_window:
            return 0
            
        return self.time_window - time_passed

# 创建限流器实例
from config import config
chat_limiter = RateLimiter(
    max_requests=config.rate_limit_max_requests,
    time_window=config.rate_limit_window
)
