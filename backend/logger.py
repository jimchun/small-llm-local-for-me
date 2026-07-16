"""
日志系统 - 提供统一的日志记录和错误追踪
"""
import logging
import sys
from pathlib import Path
from datetime import datetime


class Logger:
    """统一日志管理器"""
    
    def __init__(self, name="little_llm", log_dir="logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建日志器
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # 避免重复添加handler
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """配置日志处理器"""
        # 控制台handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
        
        # 文件handler - 按日期
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.log_dir / f"{today}.log"
        file_handler = logging.FileHandler(
            log_file,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        self.logger.addHandler(file_handler)
    
    def debug(self, msg, *args):
        """记录debug日志"""
        self.logger.debug(msg, *args)
    
    def info(self, msg, *args):
        """记录info日志"""
        self.logger.info(msg, *args)
    
    def warning(self, msg, *args):
        """记录warning日志"""
        self.logger.warning(msg, *args)
    
    def error(self, msg, *args):
        """记录error日志"""
        self.logger.error(msg, *args)
    
    def critical(self, msg, *args):
        """记录critical日志"""
        self.logger.critical(msg, *args)
    
    def exception(self, msg, *args):
        """记录异常日志(包含堆栈)"""
        self.logger.exception(msg, *args)


# 全局日志实例
logger = Logger()
