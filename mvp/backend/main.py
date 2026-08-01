"""
Little LLM MVP - 极简本地知识问答后端
核心卖点：强制引用机制，拒绝幻觉
"""
import os
import requests
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="Little LLM MVP")

# 前端文件路径
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

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

# 强制引用 Prompt 模板 —— 防幻觉核心
SYSTEM_PROMPT = """你是一个严格基于证据的问答助手。
请仅根据以下【参考资料】回答用户的问题。

要求：
1. 回答必须完全基于参考资料，不得添加任何参考资料之外的内容。
2. 每个事实性陈述后必须标注引用来源，格式为 [来源名称]。
3. 如果参考资料中没有相关信息，必须明确回复：「参考资料中没有相关信息，无法回答。」
4. 不得推测、编造或补充任何信息。

【参考资料】
{context}
"""


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[dict]
    has_sufficient_context: bool


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
    流程：问题 → 维基百科检索 → 强制引用Prompt → Ollama推理 → 返回答案+来源
    """
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")

    # 1. 从维基百科获取参考资料
    context, sources = fetch_wikipedia(question)

    if not context:
        return QueryResponse(
            answer="抱歉，未能从维基百科找到与问题相关的资料。",
            sources=[],
            has_sufficient_context=False,
        )

    # 2. 构造强制引用 Prompt
    system = SYSTEM_PROMPT.format(context=context)
    full_prompt = f"{system}\n\n用户问题：{question}\n\n请基于以上参考资料回答："

    # 3. 调用本地模型
    answer = call_ollama(full_prompt)

    return QueryResponse(
        answer=answer,
        sources=sources,
        has_sufficient_context=True,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9821)
