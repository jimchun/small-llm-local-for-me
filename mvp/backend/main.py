"""
Little LLM MVP - 极简本地知识问答后端
核心卖点：强制引用机制，拒绝幻觉
"""
import os
import json
import requests
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="Little LLM MVP")

# 前端文件路径
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# 对话历史文件
CONVERSATION_FILE = DATA_DIR / "conversations.json"

# 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ollama 配置
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "deepseek-r1:1.5b"

# 强制引用 Prompt 模板 —— 知识问答模式
KNOWLEDGE_PROMPT = """你是一个严格基于证据的问答助手。
请仅根据以下【参考资料】回答用户的问题。

要求：
1. 回答必须完全基于参考资料，不得添加任何参考资料之外的内容。
2. 每个事实性陈述后必须标注引用来源，格式为 [来源名称]。
3. 如果参考资料中没有相关信息，必须明确回复：「参考资料中没有相关信息，无法回答。」
4. 不得推测、编造或补充任何信息。

【参考资料】
{context}
"""

# 日常对话 Prompt 模板 —— 聊天模式
CHAT_PROMPT = """你是一个友好的AI助手。请用简洁、自然的方式与用户交流。

对话历史：
{history}

用户问题：{question}

请用友好、简洁的方式回答（控制在100字以内）："""

# 判断是否为知识类问题
KNOWLEDGE_KEYWORDS = [
    "什么", "是什么", "什么是", "怎么", "为什么", "如何", "哪个", "哪些",
    "解释", "介绍", "定义", "原理", "概念", "历史", "区别", "比较",
    "计算", "公式", "方法", "步骤", "原因", "结果", "影响"
]

# 日常对话关键词
CHAT_KEYWORDS = [
    "你好", "您好", "嗨", "hi", "hello", "聊天", "只是", "不需要",
    "谢谢", "感谢", "再见", "好的", "明白了", "知道了"
]


class QueryRequest(BaseModel):
    question: str
    session_id: str = "default"


class QueryResponse(BaseModel):
    answer: str
    sources: list[dict]
    has_sufficient_context: bool
    mode: str = "knowledge"  # "knowledge" or "chat"


def load_conversation(session_id: str) -> list[dict]:
    """加载对话历史"""
    if not CONVERSATION_FILE.exists():
        return []
    try:
        with open(CONVERSATION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get(session_id, [])
    except Exception:
        return []


def save_conversation(session_id: str, history: list[dict]):
    """保存对话历史"""
    try:
        data = {}
        if CONVERSATION_FILE.exists():
            with open(CONVERSATION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        data[session_id] = history
        with open(CONVERSATION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[保存对话历史失败] {e}")


def is_knowledge_query(question: str) -> bool:
    """判断是否为知识类问题"""
    q = question.lower()
    # 包含知识类关键词
    for kw in KNOWLEDGE_KEYWORDS:
        if kw in q:
            return True
    # 问题长度较长，可能是知识查询
    if len(question) > 10:
        return True
    return False


def is_chat_query(question: str) -> bool:
    """判断是否为日常对话"""
    q = question.lower()
    for kw in CHAT_KEYWORDS:
        if kw in q:
            return True
    # 问题很短，可能是闲聊
    if len(question) < 5:
        return True
    return False


def format_history(history: list[dict], max_turns: int = 5) -> str:
    """格式化对话历史"""
    recent = history[-max_turns:] if len(history) > max_turns else history
    lines = []
    for item in recent:
        lines.append(f"用户: {item['question']}")
        lines.append(f"助手: {item['answer']}")
    return "\n".join(lines)


@app.get("/history/{session_id}")
def get_history(session_id: str):
    """获取对话历史"""
    history = load_conversation(session_id)
    return {"session_id": session_id, "count": len(history), "history": history}


@app.delete("/history/{session_id}")
def clear_history(session_id: str):
    """清空对话历史"""
    save_conversation(session_id, [])
    return {"status": "ok", "message": f"已清空会话 {session_id}"}


def fetch_wikipedia(query: str, lang: str = "zh") -> tuple[str, list[dict]]:
    """
    从维基百科获取参考资料
    返回 (拼接后的上下文字符串, 来源列表)
    """
    sources = []
    context_parts = []

    # 第一步：搜索相关词条
    search_url = f"https://{lang}.wikipedia.org/w/api.php"
    search_params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": 3,  # 最多取3篇
        "format": "json",
        "utf8": 1,
    }

    try:
        resp = requests.get(search_url, params=search_params, timeout=10)
        resp.raise_for_status()
        results = resp.json().get("query", {}).get("search", [])
    except Exception as e:
        print(f"[维基百科搜索失败] {e}")
        return "", []

    if not results:
        # 中文无结果时尝试英文
        if lang == "zh":
            return fetch_wikipedia(query, lang="en")
        return "", []

    # 第二步：获取每篇词条的摘要
    page_ids = [r["pageid"] for r in results]
    summary_params = {
        "action": "query",
        "pageids": "|".join(str(pid) for pid in page_ids),
        "prop": "extracts",
        "exintro": True,  # 只要引言部分，节省token
        "explaintext": True,  # 纯文本，不要HTML
        "format": "json",
    }

    try:
        resp = requests.get(search_url, params=summary_params, timeout=10)
        resp.raise_for_status()
        pages = resp.json().get("query", {}).get("pages", {})
    except Exception as e:
        print(f"[维基百科摘要获取失败] {e}")
        return "", []

    # 第三步：拼接上下文
    for page_id, page in pages.items():
        title = page.get("title", "未知")
        extract = page.get("extract", "").strip()
        if extract:
            # 限制每篇长度，避免超出模型上下文
            truncated = extract[:800]
            context_parts.append(f"[{title}] {truncated}")
            # 构造来源信息
            wiki_link = f"https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}"
            sources.append({"title": title, "url": wiki_link, "snippet": extract[:200]})

    return "\n\n".join(context_parts), sources


def call_ollama(prompt: str) -> str:
    """调用本地 Ollama 模型"""
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,  # 低温，减少幻觉
            "num_predict": 512,
        },
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=60)
        resp.raise_for_status()
        return resp.json().get("response", "")
    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail="无法连接 Ollama，请确认已启动且安装了 deepseek-r1:1.5b 模型",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"模型调用失败: {e}")


@app.get("/health")
def health():
    """健康检查"""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index():
    """前端页面"""
    html_file = FRONTEND_DIR / "index.html"
    if not html_file.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
    return html_file.read_text(encoding="utf-8")


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    """
    核心查询接口
    流程：意图识别 → 知识问答/日常对话 → 保存历史 → 返回答案
    """
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")

    session_id = req.session_id
    history = load_conversation(session_id)

    # 判断模式：日常对话 vs 知识问答
    if is_chat_query(question) and not is_knowledge_query(question):
        # 日常对话模式 - 使用上下文，不走维基百科
        history_text = format_history(history)
        prompt = CHAT_PROMPT.format(history=history_text, question=question)
        answer = call_ollama(prompt)

        # 保存对话
        history.append({
            "question": question,
            "answer": answer,
            "mode": "chat",
            "time": datetime.now().isoformat()
        })
        save_conversation(session_id, history)

        return QueryResponse(
            answer=answer,
            sources=[],
            has_sufficient_context=True,
            mode="chat"
        )
    else:
        # 知识问答模式 - 维基百科检索 + 强制引用
        context, sources = fetch_wikipedia(question)

        if not context:
            # 维基百科无结果时，用日常对话兜底，不再返回"无法回答"
            history_text = format_history(history)
            prompt = CHAT_PROMPT.format(history=history_text, question=question)
            answer = call_ollama(prompt)

            history.append({
                "question": question,
                "answer": answer,
                "mode": "chat",
                "time": datetime.now().isoformat()
            })
            save_conversation(session_id, history)

            return QueryResponse(
                answer=answer,
                sources=[],
                has_sufficient_context=False,
                mode="chat"
            )

        # 构造强制引用 Prompt + 上下文历史
        history_text = format_history(history, max_turns=3)
        system = KNOWLEDGE_PROMPT.format(context=context)
        if history_text:
            full_prompt = f"对话历史:\n{history_text}\n\n{system}\n\n用户问题：{question}\n\n请基于以上参考资料回答："
        else:
            full_prompt = f"{system}\n\n用户问题：{question}\n\n请基于以上参考资料回答："

        answer = call_ollama(full_prompt)

        # 保存对话
        history.append({
            "question": question,
            "answer": answer,
            "mode": "knowledge",
            "time": datetime.now().isoformat()
        })
        save_conversation(session_id, history)

        return QueryResponse(
            answer=answer,
            sources=sources,
            has_sufficient_context=True,
            mode="knowledge"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9821)
