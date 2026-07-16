"""
用户画像系统 - 支持静态画像和动态记忆
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from logger import logger  # Logger 全局实例


class UserProfile:
    """用户画像管理器"""
    
    def __init__(self, profile_file: str = "data/user_profile.json"):
        self.profile_file = Path(profile_file)
        self.profile_data = self._load_profile()
        logger.info(f"用户画像系统初始化: {self.profile_file}")
    
    def _load_profile(self) -> Dict:
        """加载用户画像"""
        if self.profile_file.exists():
            try:
                with open(self.profile_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.debug(f"加载用户画像成功")
                return data
            except Exception as e:
                logger.error(f"加载用户画像失败: {e}")
        
        # 默认空画像
        return {
            "static_profile": {
                "name": "",
                "occupation": "",
                "background": "",
                "preferences": ""
            },
            "dynamic_memory": [],
            "private_docs": []
        }
    
    def save_profile(self):
        """保存用户画像"""
        try:
            self.profile_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.profile_file, 'w', encoding='utf-8') as f:
                json.dump(self.profile_data, f, ensure_ascii=False, indent=2)
            logger.info("用户画像保存成功")
        except Exception as e:
            logger.error(f"保存用户画像失败: {e}")
    
    def update_static_profile(self, profile: Dict):
        """
        更新静态画像
        
        Args:
            profile: 画像字段字典，如 {name: "张三", occupation: "工程师"}
        """
        self.profile_data["static_profile"].update(profile)
        self.save_profile()
        logger.info("静态画像更新成功")
    
    def get_static_profile(self) -> Dict:
        """获取静态画像"""
        return self.profile_data.get("static_profile", {})
    
    def add_dynamic_memory(self, content: str, metadata: Optional[Dict] = None):
        """
        添加动态记忆
        
        Args:
            content: 记忆内容
            metadata: 元数据（如时间、来源等）
        """
        memory_item = {
            "content": content,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat()
        }
        
        self.profile_data["dynamic_memory"].append(memory_item)
        self.save_profile()
        logger.info(f"添加动态记忆: {content[:50]}...")
    
    def get_dynamic_memories(self, limit: int = 10) -> List[Dict]:
        """
        获取动态记忆
        
        Args:
            limit: 返回数量限制
        
        Returns:
            记忆列表
        """
        memories = self.profile_data.get("dynamic_memory", [])
        # 按时间倒序返回最新的
        return memories[-limit:][::-1]
    
    def search_dynamic_memory(self, query: str, limit: int = 5) -> List[Dict]:
        """
        搜索动态记忆（简单关键词匹配）
        
        Args:
            query: 搜索关键词
            limit: 返回数量限制
        
        Returns:
            匹配的记忆列表
        """
        memories = self.profile_data.get("dynamic_memory", [])
        results = []
        
        for memory in memories:
            content = memory.get("content", "")
            # 简单的关键词匹配
            if query.lower() in content.lower():
                results.append(memory)
                if len(results) >= limit:
                    break
        
        logger.debug(f"动态记忆搜索 '{query}'，返回 {len(results)} 条结果")
        return results
    
    def get_profile_for_prompt(self) -> str:
        """
        生成用于 Prompt 注入的画像文本
        
        Returns:
            格式化的画像文本
        """
        static = self.get_static_profile()
        parts = []
        
        if static.get("name"):
            parts.append(f"用户姓名: {static['name']}")
        if static.get("occupation"):
            parts.append(f"职业: {static['occupation']}")
        if static.get("background"):
            parts.append(f"背景: {static['background']}")
        if static.get("preferences"):
            parts.append(f"偏好: {static['preferences']}")
        
        if not parts:
            return ""
        
        return "【用户画像】\n" + "\n".join(parts)
    
    def add_private_doc(self, doc_path: str, content: str, metadata: Optional[Dict] = None):
        """
        添加私有文档
        
        Args:
            doc_path: 文档路径
            content: 文档内容
            metadata: 元数据
        """
        doc_item = {
            "path": doc_path,
            "content": content,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat()
        }
        
        self.profile_data["private_docs"].append(doc_item)
        self.save_profile()
        logger.info(f"添加私有文档: {doc_path}")
    
    def get_private_docs(self) -> List[Dict]:
        """获取所有私有文档"""
        return self.profile_data.get("private_docs", [])


# 全局实例
user_profile = UserProfile()
