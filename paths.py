import os
import sys

def get_base_path():
    """获取应用程序基础路径
    
    如果是打包后的exe，返回exe所在目录
    如果是开发环境，返回当前文件所在目录
    """
    if getattr(sys, 'frozen', False):
        # 如果是打包后的exe
        return os.path.dirname(sys.executable)
    else:
        # 如果是开发环境
        return os.path.dirname(os.path.abspath(__file__))

def get_template_path():
    """获取模板目录路径
    
    如果是打包后的exe，返回exe所在目录下的templates
    如果是开发环境，返回templates目录
    """
    if getattr(sys, 'frozen', False):
        # 如果是打包后的exe
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    else:
        # 如果是开发环境
        return "templates"
    
def get_static_path():
    """获取静态文件目录路径
    
    如果是打包后的exe，返回exe所在目录下的static
    如果是开发环境，返回static目录
    """
    if getattr(sys, 'frozen', False):
        # 如果是打包后的exe
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    else:
        # 如果是开发环境
        return "static"
