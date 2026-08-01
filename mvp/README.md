# Little LLM MVP

让每个人的电脑，都能运行自己的 AI。

## 快速开始

### 环境要求
- Windows 10/11
- Python 3.11+
- [Ollama](https://ollama.com/)

### 一键启动

双击运行 `start.bat`，自动完成：
1. 检查 Python 环境
2. 创建虚拟环境并安装依赖
3. 检查 Ollama 服务
4. 下载模型（首次运行约1.1GB）
5. 启动后端并打开浏览器

### 手动启动

```bash
# 1. 安装依赖
cd backend
pip install -r requirements.txt

# 2. 启动后端
python main.py
# → http://localhost:9821

# 3. 打开前端
# 浏览器打开 frontend/index.html
```

## 核心特性

- **强制引用**：每个回答必须标注来源，拒绝幻觉
- **知识外包**：维基百科实时检索，小模型只做逻辑推理
- **本地运行**：数据完全本地，隐私零泄露
- **一键启动**：无需复杂配置，开箱即用

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | FastAPI (端口 9821) |
| 推理 | Ollama + DeepSeek-R1 1.5B |
| 知识源 | 维基百科 API |
| 前端 | 单文件 HTML |

## 项目结构

```
mvp/
├── backend/
│   ├── main.py          # FastAPI 后端
│   └── requirements.txt # 依赖
├── frontend/
│   └── index.html       # Web 前端
├── start.bat            # 一键启动
└── README.md            # 本文件
```

## 开源协议

Apache 2.0
