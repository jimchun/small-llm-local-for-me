"""
智能文件夹监控系统 - 持续监控指定文件夹，自动提取文档到向量库
"""
import json
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Set
from datetime import datetime
from threading import Thread, Event

from vector_store import add_to_vector_store
from llm_engine import llm
from logger import logger


class FileMetadata:
    """文件元数据"""
    def __init__(self, file_path: str, modified_time: float, file_size: int, content_hash: str):
        self.file_path = file_path
        self.modified_time = modified_time
        self.file_size = file_size
        self.content_hash = content_hash
        self.processed_time: Optional[float] = None  # 处理时间
    
    def to_dict(self) -> Dict:
        return {
            "file_path": self.file_path,
            "modified_time": self.modified_time,
            "file_size": self.file_size,
            "content_hash": self.content_hash,
            "processed_time": self.processed_time
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'FileMetadata':
        meta = FileMetadata(
            data["file_path"],
            data["modified_time"],
            data["file_size"],
            data["content_hash"]
        )
        meta.processed_time = data.get("processed_time")
        return meta


class FolderMonitor:
    """文件夹监控器"""
    
    def __init__(self, config_file: str = "data/folder_monitor.json"):
        """
        初始化监控器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = Path(config_file)
        self.config = self._load_config()
        self.metadata_file = Path("data/file_metadata.json")
        self.file_metadata: Dict[str, FileMetadata] = self._load_metadata()
        
        # 监控配置
        self.scan_interval = self.config.get("scan_interval", 300)  # 默认5分钟
        self.file_types = set(self.config.get("file_types", [".txt", ".md", ".pdf", ".docx"]))
        self.recursive = self.config.get("recursive", True)
        
        # 运行状态
        self._stop_event = Event()
        self._thread: Optional[Thread] = None
        self._running = False
        
        logger.info(f"文件夹监控器初始化完成，扫描间隔: {self.scan_interval}秒")
    
    def _load_config(self) -> Dict:
        """加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载监控配置失败: {e}")
        
        # 默认配置
        return {
            "folders": [],
            "scan_interval": 300,
            "file_types": [".txt", ".md", ".pdf", ".docx"],
            "recursive": True,
            "enabled": False
        }
    
    def _save_config(self):
        """保存配置"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存监控配置失败: {e}")
    
    def _load_metadata(self) -> Dict[str, FileMetadata]:
        """加载文件元数据"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {k: FileMetadata.from_dict(v) for k, v in data.items()}
            except Exception as e:
                logger.error(f"加载文件元数据失败: {e}")
        return {}
    
    def _save_metadata(self):
        """保存文件元数据"""
        try:
            self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
            data = {k: v.to_dict() for k, v in self.file_metadata.items()}
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存文件元数据失败: {e}")
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件内容哈希"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()
        except Exception as e:
            logger.error(f"计算文件哈希失败: {file_path}, {e}")
            return ""
    
    def add_folder(self, folder_path: str) -> bool:
        """
        添加监控文件夹
        
        Args:
            folder_path: 文件夹路径
        
        Returns:
            是否添加成功
        """
        folder = Path(folder_path)
        if not folder.exists():
            logger.error(f"文件夹不存在: {folder_path}")
            return False
        
        if not folder.is_dir():
            logger.error(f"路径不是文件夹: {folder_path}")
            return False
        
        # 避免重复添加
        if folder_path in self.config["folders"]:
            logger.warning(f"文件夹已在监控列表中: {folder_path}")
            return False
        
        self.config["folders"].append(folder_path)
        self._save_config()
        logger.info(f"添加监控文件夹: {folder_path}")
        return True
    
    def remove_folder(self, folder_path: str) -> bool:
        """
        移除监控文件夹
        
        Args:
            folder_path: 文件夹路径
        
        Returns:
            是否移除成功
        """
        if folder_path not in self.config["folders"]:
            logger.warning(f"文件夹不在监控列表中: {folder_path}")
            return False
        
        self.config["folders"].remove(folder_path)
        self._save_config()
        logger.info(f"移除监控文件夹: {folder_path}")
        return True
    
    def get_folders(self) -> List[str]:
        """获取所有监控文件夹"""
        return self.config["folders"]
    
    def set_scan_interval(self, interval: int):
        """
        设置扫描间隔
        
        Args:
            interval: 间隔秒数
        """
        self.scan_interval = interval
        self.config["scan_interval"] = interval
        self._save_config()
        logger.info(f"更新扫描间隔: {interval}秒")
    
    def enable(self):
        """启用监控"""
        self.config["enabled"] = True
        self._save_config()
        logger.info("文件夹监控已启用")
    
    def disable(self):
        """禁用监控"""
        self.config["enabled"] = False
        self._save_config()
        logger.info("文件夹监控已禁用")
    
    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self.config.get("enabled", False)
    
    def _scan_folder(self, folder_path: str) -> List[str]:
        """
        扫描文件夹，返回所有符合条件的文件路径
        
        Args:
            folder_path: 文件夹路径
        
        Returns:
            文件路径列表
        """
        folder = Path(folder_path)
        if not folder.exists():
            return []
        
        files = []
        pattern = "**/*" if self.recursive else "*"
        
        for file_path in folder.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in self.file_types:
                files.append(str(file_path))
        
        return files
    
    def _read_file_content(self, file_path: str) -> Optional[str]:
        """
        读取文件内容
        
        Args:
            file_path: 文件路径
        
        Returns:
            文件内容，失败返回None
        """
        try:
            path = Path(file_path)
            ext = path.suffix.lower()
            
            if ext in [".txt", ".md"]:
                return path.read_text(encoding='utf-8')
            elif ext == ".pdf":
                # 简化处理，实际需要PyPDF2
                return f"[PDF文件: {path.name}]"
            elif ext == ".docx":
                # 简化处理，实际需要python-docx
                return f"[Word文件: {path.name}]"
            else:
                return None
        except Exception as e:
            logger.error(f"读取文件失败: {file_path}, {e}")
            return None
    
    def _understand_and_extract(self, content: str, file_name: str) -> Optional[Dict]:
        """
        使用LLM理解文档内容并提取关键信息
        
        Args:
            content: 文档内容
            file_name: 文件名
        
        Returns:
            提取的信息字典，包含summary, keywords, category
        """
        if not content or len(content.strip()) < 50:
            return None
        
        # 截断过长内容
        max_chars = 3000
        if len(content) > max_chars:
            content = content[:max_chars] + "..."
        
        prompt = f"""请分析以下文档内容，提取关键信息：

文件名：{file_name}

文档内容：
{content}

请提取：
1. 摘要（100字以内）
2. 关键词（3-5个，用逗号分隔）
3. 分类（从以下选择：技术、产品、市场、管理、其他）

请以JSON格式返回：
{{
  "summary": "摘要内容",
  "keywords": "关键词1,关键词2,关键词3",
  "category": "分类"
}}
"""
        
        try:
            response = llm.generate(prompt)
            # 尝试从响应中提取JSON
            answer = response.get("answer", "")
            
            # 简单的JSON提取（实际应该更健壮）
            if "{" in answer and "}" in answer:
                start = answer.find("{")
                end = answer.rfind("}") + 1
                json_str = answer[start:end]
                
                # 清理JSON字符串
                json_str = json_str.replace('\n', ' ').replace('\r', ' ')
                
                import json
                try:
                    result = json.loads(json_str)
                    return result
                except:
                    pass
            
            # 如果解析失败，返回默认值
            return {
                "summary": answer[:100] if answer else "",
                "keywords": file_name,
                "category": "其他"
            }
        except Exception as e:
            logger.error(f"LLM理解文档失败: {e}")
            return None
    
    def _process_file(self, file_path: str) -> bool:
        """
        处理单个文件：读取、理解、向量化
        
        Args:
            file_path: 文件路径
        
        Returns:
            是否处理成功
        """
        try:
            # 读取内容
            content = self._read_file_content(file_path)
            if not content:
                return False
            
            # 计算哈希
            content_hash = self._calculate_file_hash(file_path)
            
            # 检查是否需要处理（文件是否修改）
            if file_path in self.file_metadata:
                old_meta = self.file_metadata[file_path]
                if old_meta.content_hash == content_hash:
                    logger.debug(f"文件未修改，跳过: {file_path}")
                    return False
            
            # 获取文件信息
            path = Path(file_path)
            stat = path.stat()
            
            # 使用LLM理解文档
            extraction = self._understand_and_extract(content, path.name)
            if not extraction:
                logger.warning(f"无法理解文档: {file_path}")
                return False
            
            # 构建向量库文档
            doc_text = f"""文件名: {path.name}
分类: {extraction.get('category', '其他')}
关键词: {extraction.get('keywords', '')}
摘要: {extraction.get('summary', '')}
原文内容:
{content}
"""
            
            metadata = {
                "source": "folder_monitor",
                "file_path": file_path,
                "file_name": path.name,
                "category": extraction.get('category', '其他'),
                "keywords": extraction.get('keywords', ''),
                "summary": extraction.get('summary', ''),
                "processed_time": time.time()
            }
            
            # 添加到向量库
            add_to_vector_store(
                documents=[doc_text],
                metadatas=[metadata],
                ids=[f"monitor_{content_hash}"]
            )
            
            # 更新元数据
            self.file_metadata[file_path] = FileMetadata(
                file_path=file_path,
                modified_time=stat.st_mtime,
                file_size=stat.st_size,
                content_hash=content_hash
            )
            self.file_metadata[file_path].processed_time = time.time()
            
            logger.info(f"成功处理文件: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"处理文件失败: {file_path}, {e}")
            return False
    
    def scan_all_folders(self):
        """扫描所有监控文件夹"""
        if not self.config.get("enabled", False):
            return
        
        logger.info("开始扫描所有监控文件夹...")
        
        total_files = 0
        processed_files = 0
        
        for folder_path in self.config["folders"]:
            files = self._scan_folder(folder_path)
            total_files += len(files)
            
            for file_path in files:
                if self._process_file(file_path):
                    processed_files += 1
        
        # 保存元数据
        self._save_metadata()
        
        logger.info(f"扫描完成，总文件数: {total_files}，新处理: {processed_files}")
    
    def start(self):
        """启动后台监控线程"""
        if self._running:
            logger.warning("监控器已在运行")
            return
        
        self._running = True
        self._stop_event.clear()
        
        # 立即执行一次扫描
        self.scan_all_folders()
        
        # 启动后台线程
        self._thread = Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        
        logger.info(f"文件夹监控已启动，间隔: {self.scan_interval}秒")
    
    def stop(self):
        """停止监控"""
        if not self._running:
            return
        
        self._running = False
        self._stop_event.set()
        
        if self._thread:
            self._thread.join(timeout=5)
        
        logger.info("文件夹监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while not self._stop_event.is_set():
            # 等待指定时间或收到停止信号
            if self._stop_event.wait(timeout=self.scan_interval):
                break
            
            # 执行扫描
            try:
                self.scan_all_folders()
            except Exception as e:
                logger.error(f"扫描异常: {e}")
    
    def get_status(self) -> Dict:
        """
        获取监控状态
        
        Returns:
            状态信息字典
        """
        return {
            "enabled": self.config.get("enabled", False),
            "scan_interval": self.scan_interval,
            "folders": self.config["folders"],
            "file_types": list(self.file_types),
            "recursive": self.recursive,
            "total_monitored_files": len(self.file_metadata),
            "running": self._running
        }


# 全局实例
folder_monitor = FolderMonitor()
