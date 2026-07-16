# Little LLM - 零幻觉知识助手

轻量化本地推理核 + 联网权威知识库 AI 产品

## 🚀 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 安装 Ollama

下载并安装 Ollama：https://ollama.com/download

拉取模型：
```bash
ollama pull deepseek-r1:1.5b
```

### 3. 启动服务

**Windows 一键启动：**
```bash
start.bat
```

**手动启动：**

终端1 - 启动 API：
```bash
cd backend
python main.py
```

终端2 - 启动 GUI：
```bash
cd frontend
python gui_client.py
```

### 4. 使用

1. 在 GUI 界面输入问题
2. 选择知识源（维基百科 / 本地向量库）
3. 点击查询
4. 查看回答和引用来源

## 📁 项目结构

```
little-llm-local-for-me/
├── backend/              # FastAPI 后端
│   ├── main.py          # API 主应用（整合多知识源+意图路由+强制引用）
│   ├── config.py        # 配置文件
│   ├── knowledge_base.py # 维基百科知识库
│   ├── multi_sources.py # 多知识源管理器（权重分配算法）
│   ├── prompt_system.py # 强制引用 Prompt 系统（防幻觉）
│   ├── user_profile.py  # 用户画像系统（静态画像+动态记忆+私有文档）
│   ├── common_sense_cache.py # 常识缓存（100+条基础常识）
│   ├── vector_store.py  # 向量数据库
│   ├── llm_engine.py    # LLM 推理引擎
│   ├── logger.py        # 统一日志系统
│   └── requirements.txt # Python 依赖
├── frontend/            # PyQt6 桌面客户端
│   └── gui_client.py   # GUI 主程序
├── data/                # 数据存储
│   ├── chroma_db/      # ChromaDB 向量库
│   ├── common_sense.json # 常识缓存数据
│   └── user_profile.json # 用户画像数据
├── logs/                # 日志目录（按日期自动滚动）
├── start.bat           # Windows 启动脚本
└── README.md           # 项目说明
```

## 🔧 技术栈

- **后端**: FastAPI + ChromaDB + Ollama
- **前端**: PyQt6
- **推理模型**: DeepSeek-R1-Distill-1.5B
- **嵌入模型**: text2vec-base-chinese
- **知识源**: 中文维基百科 API

## 📖 核心特性

✅ **零幻觉**: 所有回答均来自权威数据源  
✅ **引用溯源**: 每个回答标注引用来源，可跳转原文验证  
✅ **多知识源系统**: 维基百科 + 百度百科 + 本地向量库，自动权重分配  
✅ **强制引用机制**: Prompt 工程确保无资料时明确兜底，防止幻觉  
✅ **常识缓存**: 100+ 条本地常识，优先匹配快速响应  
✅ **用户画像**: 静态画像 + 动态记忆，上下文感知增强  
✅ **统一日志**: 控制台彩色输出 + 文件日志，便于问题追踪  
✅ **本地推理**: 全程本地运行，数据不上传云端  
✅ **联网检索**: 实时获取最新权威知识  
✅ **向量检索**: 支持本地知识库扩展  

## 🛠️ API 文档

启动服务后访问：http://localhost:9820/docs

**主要接口：**
- `POST /api/query` - 智能问答（多知识源 + 意图路由 + 强制引用）
- `POST /api/search` - 多知识源统一搜索（含权重排序）
- `POST /api/vector/search` - 向量库搜索
- `POST /api/vector/add` - 添加文档到向量库
- `GET /api/profile` - 获取用户画像
- `POST /api/profile/update` - 更新用户画像
- `POST /api/memory/add` - 添加动态记忆
- `GET /api/memory/search` - 搜索动态记忆
- `GET /api/stats` - 系统统计信息

## 📜 版本历史

### v12 (2026-07-03)

**修复内容：**
- ✅ 修复启动依赖问题：解决 `ModuleNotFoundError: No module named 'chromadb'`
- ✅ 完成 Windows 环境依赖安装（requirements.txt 中所有依赖已正确安装）
- ✅ 服务启动测试通过：
  - GET /health 返回 200 OK
  - GET / 返回服务状态信息
  - POST /api/query 接口可正常调用（LLM 推理需要时间）

**技术细节：**
- 依赖安装使用 Windows 本地 Python 3.12 环境
- 服务监听端口：9820（0.0.0.0）
- 解决端口占用问题，确保服务正常启动

## 📝 License

Apache 2.0
