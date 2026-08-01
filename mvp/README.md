# Little LLM MVP v17.2

让每个人的电脑，都能运行自己的 AI。

## 快速开始

```powershell
# 双击运行 start.bat
# 或手动启动：
cd mvp/backend
python main.py
```

访问 http://127.0.0.1:9821/

## 功能特性

### 双模式对话
- **知识问答模式**：维基百科检索 + 强制引用，拒绝幻觉
- **日常聊天模式**：自然对话，支持多轮上下文

### 对话历史
- 自动保存所有对话内容
- 支持多轮对话上下文
- 清空对话功能

### 智能识别
- 自动识别用户意图
- 短对话/问候语进入聊天模式
- 知识性问题进入问答模式

## API 接口

- `POST /query` - 智能问答
- `GET /history/{session_id}` - 获取对话历史
- `DELETE /history/{session_id}` - 清空对话

## 项目结构

```
mvp/
├── backend/
│   ├── main.py          # FastAPI 后端（双模式+上下文）
│   └── requirements.txt
├── frontend/
│   └── index.html       # 聊天界面
├── data/                # 对话历史存储
└── start.bat           # Windows 启动脚本
```

## 开源协议

Apache 2.0
