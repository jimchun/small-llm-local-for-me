"""配置文件"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent

# Ollama 配置
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "deepseek-r1:1.5b"  # 本地推理模型

# ChromaDB 配置
CHROMA_HOST = "localhost"
CHROMA_PORT = 8001
CHROMA_COLLECTION = "knowledge_base"
CHROMA_PERSIST_DIR = str(BASE_DIR / "data" / "chroma_db")

# 嵌入模型
EMBEDDING_MODEL = "shibing624/text2vec-base-chinese"

# 知识库数据源
WIKI_API_URL = "https://zh.wikipedia.org/w/api.php"
WIKI_LANGUAGE = "zh"

# API 配置
API_HOST = "0.0.0.0"
API_PORT = 9820

# 日志级别
LOG_LEVEL = "INFO"

# 多知识源配置
MULTI_SOURCES = {
    "common_sense": {
        "enabled": True,
        "weight": 1.0,
        "description": "常识缓存（最高优先级，本地快速）"
    },
    "local_vector": {
        "enabled": True,
        "weight": 0.8,
        "description": "本地向量库"
    },
    "wikipedia": {
        "enabled": True,
        "weight": 0.9,
        "description": "维基百科（权威性高）"
    },
    "baidu_baike": {
        "enabled": True,
        "weight": 0.7,
        "description": "百度百科"
    }
}

# 意图路由配置
INTENT_ROUTING = {
    "enabled": True,
    "model": OLLAMA_MODEL,  # 使用同一模型做意图分类
    "description": "A/B/C 三分类意图路由"
}

# 用户画像配置
USER_PROFILE = {
    "enabled": True,
    "file": str(BASE_DIR / "data" / "user_profile.json"),
    "inject_to_prompt": True,
    "description": "用户画像系统，支持静态画像和动态记忆"
}

# 幻觉防护配置
HALLUCINATION_GUARD = {
    "force_citation": True,
    "no_context_fallback": "根据提供的资料，无法回答这个问题",
    "confidence_threshold": 0.6,
    "description": "强制引用 + 无资料兜底"
}

# 确保数据目录存在
(BASE_DIR / "data").mkdir(exist_ok=True)
(BASE_DIR / "data" / "wiki_cache").mkdir(exist_ok=True)
(BASE_DIR / "logs").mkdir(exist_ok=True)
