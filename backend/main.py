"""FastAPI 主应用"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import uvicorn
from datetime import datetime
import os
from pathlib import Path
from vector_store import vector_store, search_vector_store, add_to_vector_store
from multi_sources import multi_source_manager, WikipediaSource, BaiduBaikeSource, LocalVectorStoreSource
from prompt_system import PromptBuilder
from user_profile import UserProfile
from common_sense_cache import CommonSenseCache
from llm_engine import generate_answer
from folder_monitor import folder_monitor
from logger import Logger
from config import LOG_LEVEL, API_PORT

import logging

# 配置日志（兼容旧代码）
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = Logger("main")

# 创建 FastAPI 应用
app = FastAPI(
    title="Little LLM API",
    description="轻量化本地推理核 + 联网权威知识库",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 数据模型 ==========
class QueryRequest(BaseModel):
    question: str
    use_vector_store: bool = False
    top_k: int = 3
    use_common_sense: bool = True
    use_multi_sources: bool = True


class QueryResponse(BaseModel):
    answer: str
    sources: List[dict]
    model: str
    context_used: int
    intent: str  # A/B/C
    cache_hit: bool = False


class SearchRequest(BaseModel):
    query: str
    limit: int = 5


class UserProfileRequest(BaseModel):
    name: Optional[str] = None
    occupation: Optional[str] = None
    background: Optional[str] = None
    preferences: Optional[str] = None


class MemoryRequest(BaseModel):
    content: str
    metadata: Optional[Dict] = None


class AddDocumentRequest(BaseModel):
    documents: List[str]
    metadatas: Optional[List[dict]] = None
    ids: Optional[List[str]] = None


class FolderImportRequest(BaseModel):
    folder_path: str
    file_types: Optional[List[str]] = [".txt", ".md", ".pdf", ".docx"]
    recursive: bool = True


class FolderScanRequest(BaseModel):
    folder_path: str
    file_types: Optional[List[str]] = [".txt", ".md", ".pdf", ".docx"]
    recursive: bool = True


# ========== 初始化全局组件 ==========
logger.info("初始化全局组件...")

# 用户画像
user_profile = UserProfile()

# 常识缓存
common_sense_cache = CommonSenseCache()

# Prompt 构建器
prompt_builder = PromptBuilder()

# 多知识源管理器 - 注册所有知识源
multi_source_manager.add_source(WikipediaSource())
multi_source_manager.add_source(BaiduBaikeSource())

# 延迟注册本地向量源（等 vector_store 初始化后）
try:
    local_vector_source = LocalVectorStoreSource(vector_store)
    multi_source_manager.add_source(local_vector_source)
    logger.info("本地向量库知识源注册成功")
except Exception as e:
    logger.warning(f"本地向量库知识源注册失败: {e}")

logger.info("全局组件初始化完成")

# 自动启动文件夹监控
if folder_monitor.is_enabled():
    folder_monitor.start()
    logger.info("文件夹监控服务已自动启动")


# ========== API 端点 ==========
@app.get("/")
async def root():
    """根路径"""
    return {
        "status": "running",
        "service": "Little LLM API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}


@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    智能问答接口 - 整合多知识源 + 意图路由 + 强制引用
    
    流程：
    1. 常识缓存检查（最快，本地）
    2. 意图分类（A/B/C 三分类）
    3. 多知识源检索（权重分配）
    4. 用户画像注入
    5. 强制引用 Prompt 构建
    6. LLM 推理生成
    7. 动态记忆沉淀
    """
    try:
        logger.info(f"收到查询请求: {request.question}")
        
        # 步骤0: 常识缓存检查（最快）
        cache_hit = False
        cache_result = None
        if request.use_common_sense:
            logger.debug("检查常识缓存...")
            cache_result = common_sense_cache.search(request.question)
            if cache_result:
                logger.info("常识缓存命中，直接返回")
                cache_hit = True
                return QueryResponse(
                    answer=cache_result["content"],
                    sources=[{
                        "index": 1,
                        "title": f"常识缓存 - {cache_result.get('metadata', {}).get('category', '通用')}",
                        "content": cache_result["content"],
                        "url": "",
                        "source": cache_result.get("metadata", {}).get("source", "常识缓存")
                    }],
                    model="local_cache",
                    context_used=1,
                    intent="B",  # 常识属于公共知识
                    cache_hit=True
                )
        
        # 步骤1: 意图分类
        logger.debug("意图分类...")
        intent_prompt = prompt_builder.build_intent_classification_prompt(request.question)
        intent_result = generate_answer(intent_prompt, [])
        intent = prompt_builder.parse_intent_result(intent_result["answer"])
        logger.info(f"意图分类结果: {intent}")
        
        # 步骤2: 多知识源检索
        all_sources = []
        
        if intent == "A":
            # A类：仅涉及用户个人记忆/私有文档
            logger.info("意图A: 检索用户个人记忆...")
            memories = user_profile.search_dynamic_memory(request.question, limit=request.top_k)
            for idx, mem in enumerate(memories):
                all_sources.append({
                    "index": idx + 1,
                    "title": "用户记忆",
                    "content": mem["content"],
                    "url": "",
                    "source": "用户动态记忆"
                })
        
        elif intent == "B":
            # B类：仅涉及公共常识/百科/事实
            logger.info("意图B: 检索公共知识...")
            if request.use_multi_sources:
                multi_results = multi_source_manager.search(request.question, limit=request.top_k)
                for idx, res in enumerate(multi_results):
                    all_sources.append({
                        "index": idx + 1,
                        "title": res["metadata"].get("title", "未知"),
                        "content": res["content"],
                        "url": res["metadata"].get("url", ""),
                        "source": res["metadata"].get("source", "未知来源")
                    })
            
            if request.use_vector_store:
                vector_results = search_vector_store(request.question, n_results=request.top_k)
                for idx, res in enumerate(vector_results, start=len(all_sources) + 1):
                    all_sources.append({
                        "index": idx,
                        "title": "本地知识库",
                        "content": res["content"],
                        "url": "",
                        "source": "本地向量库"
                    })
        
        elif intent == "C":
            # C类：需要结合公共知识和用户个人情况
            logger.info("意图C: 检索公共知识 + 用户记忆...")
            
            # 公共知识
            if request.use_multi_sources:
                multi_results = multi_source_manager.search(request.question, limit=request.top_k)
                for idx, res in enumerate(multi_results):
                    all_sources.append({
                        "index": idx + 1,
                        "title": res["metadata"].get("title", "未知"),
                        "content": res["content"],
                        "url": res["metadata"].get("url", ""),
                        "source": res["metadata"].get("source", "未知来源")
                    })
            
            # 用户记忆
            memories = user_profile.search_dynamic_memory(request.question, limit=request.top_k)
            for idx, mem in enumerate(memories, start=len(all_sources) + 1):
                all_sources.append({
                    "index": idx,
                    "title": "用户记忆",
                    "content": mem["content"],
                    "url": "",
                    "source": "用户动态记忆"
                })
        
        # 步骤3: 用户画像注入
        user_profile_text = ""
        if intent in ["A", "C"]:
            user_profile_text = user_profile.get_profile_for_prompt()
            if user_profile_text:
                logger.debug(f"注入用户画像: {len(user_profile_text)} 字符")
        
        # 步骤4: 强制引用 Prompt 构建
        if all_sources:
            logger.debug("构建强制引用 Prompt...")
            context_texts = [s["content"] for s in all_sources]
            prompt = prompt_builder.build_strict_prompt(request.question, context_texts, user_profile_text)
        else:
            logger.warning("无检索结果，使用无上下文 Prompt")
            prompt = prompt_builder.build_no_context_prompt(request.question, user_profile_text)
        
        # 步骤5: LLM 推理生成
        logger.debug("调用 LLM 推理...")
        result = generate_answer(prompt, [])
        
        # 步骤6: 动态记忆沉淀（可选）
        if intent in ["A", "C"] and user_profile_text:
            try:
                memory_content = f"Q: {request.question}\nA: {result['answer'][:200]}"
                user_profile.add_dynamic_memory(memory_content, {"intent": intent})
                logger.debug("动态记忆沉淀完成")
            except Exception as e:
                logger.warning(f"动态记忆沉淀失败: {e}")
        
        logger.info(f"查询完成，使用 {len(all_sources)} 个来源，意图: {intent}")
        
        return QueryResponse(
            answer=result["answer"],
            sources=all_sources,
            model=result["model"],
            context_used=result["context_used"],
            intent=intent,
            cache_hit=cache_hit
        )
        
    except Exception as e:
        logger.error(f"查询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/search")
async def search(request: SearchRequest):
    """
    多知识源搜索接口（仅检索，不生成回答）
    """
    try:
        results = multi_source_manager.search(request.query, limit=request.limit)
        return {
            "query": request.query,
            "results": [
                {
                    "content": r["content"],
                    "metadata": r["metadata"],
                    "source": r["metadata"].get("source", "未知")
                }
                for r in results
            ],
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vector/search")
async def vector_search(request: SearchRequest):
    """
    向量库搜索接口（自动查询L1+L2）
    """
    try:
        results = search_vector_store(request.query, n_results=request.limit)
        return {
            "query": request.query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"向量搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vector/stats")
async def vector_stats():
    """
    获取向量库各层统计信息（L1/L2文档数、命中率、容量等）
    """
    try:
        stats = vector_store.get_stats()
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取向量库统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vector/auto_promote")
async def vector_auto_promote():
    """
    自动将L2中高频访问的文档提升到L1热缓存
    """
    try:
        count = vector_store.auto_promote(min_access_count=3)
        return {
            "status": "success",
            "promoted_count": count,
            "message": f"已提升 {count} 条文档到L1热缓存"
        }
    except Exception as e:
        logger.error(f"自动提升失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/vector/add")
async def add_documents(request: AddDocumentRequest):
    """
    添加文档到向量库
    """
    try:
        add_to_vector_store(request.documents, request.metadatas, request.ids)
        return {
            "status": "success",
            "added_count": len(request.documents)
        }
    except Exception as e:
        logger.error(f"添加文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 用户画像 API ==========
@app.get("/api/profile")
async def get_profile():
    """获取用户画像"""
    try:
        profile = user_profile.get_static_profile()
        return {
            "status": "success",
            "profile": profile
        }
    except Exception as e:
        logger.error(f"获取用户画像失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/profile/update")
async def update_profile(request: UserProfileRequest):
    """更新用户静态画像"""
    try:
        profile_dict = {}
        if request.name is not None:
            profile_dict["name"] = request.name
        if request.occupation is not None:
            profile_dict["occupation"] = request.occupation
        if request.background is not None:
            profile_dict["background"] = request.background
        if request.preferences is not None:
            profile_dict["preferences"] = request.preferences
        
        user_profile.update_static_profile(profile_dict)
        return {
            "status": "success",
            "message": "用户画像更新成功"
        }
    except Exception as e:
        logger.error(f"更新用户画像失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/memory/add")
async def add_memory(request: MemoryRequest):
    """添加动态记忆"""
    try:
        user_profile.add_dynamic_memory(
            content=request.content,
            metadata=request.metadata
        )
        return {
            "status": "success",
            "message": "动态记忆添加成功"
        }
    except Exception as e:
        logger.error(f"添加动态记忆失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/memory/search")
async def search_memory(query: str, limit: int = 5):
    """搜索动态记忆"""
    try:
        results = user_profile.search_dynamic_memory(query, limit)
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"搜索动态记忆失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 统计信息 API ==========
@app.get("/api/stats")
async def get_stats():
    """获取系统统计信息"""
    try:
        cache_stats = common_sense_cache.get_stats()
        vector_stats = vector_store.get_stats()
        
        return {
            "status": "success",
            "stats": {
                "common_sense_cache": cache_stats,
                "vector_store": vector_stats,
                "multi_sources": {
                    "sources": [s.name for s in multi_source_manager.sources],
                    "count": len(multi_source_manager.sources)
                },
                "user_profile": {
                    "dynamic_memory_count": len(user_profile.get_dynamic_memories(limit=1000)),
                    "has_static_profile": bool(user_profile.get_static_profile().get("name"))
                },
                "folder_monitor": folder_monitor.get_status()
            }
        }
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 文件夹导入 API ==========
def scan_folder(folder_path: str, file_types: List[str] = None, recursive: bool = True) -> Dict:
    """
    扫描文件夹，返回文件列表和统计信息
    
    Args:
        folder_path: 文件夹路径
        file_types: 文件类型列表，如 [".txt", ".md"]
        recursive: 是否递归扫描子文件夹
    
    Returns:
        包含文件列表和统计信息的字典
    """
    if file_types is None:
        file_types = [".txt", ".md", ".pdf", ".docx"]
    
    folder = Path(folder_path)
    if not folder.exists():
        raise ValueError(f"文件夹不存在: {folder_path}")
    
    if not folder.is_dir():
        raise ValueError(f"路径不是文件夹: {folder_path}")
    
    files = []
    if recursive:
        for ext in file_types:
            files.extend(folder.rglob(f"*{ext}"))
    else:
        for ext in file_types:
            files.extend(folder.glob(f"*{ext}"))
    
    # 按文件大小排序
    files_info = []
    total_size = 0
    for file in files:
        size = file.stat().st_size
        total_size += size
        files_info.append({
            "path": str(file),
            "name": file.name,
            "size": size,
            "size_human": f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"
        })
    
    return {
        "folder_path": str(folder.absolute()),
        "files": files_info,
        "total_files": len(files),
        "total_size": total_size,
        "total_size_human": f"{total_size / 1024:.1f} KB" if total_size < 1024 * 1024 else f"{total_size / (1024 * 1024):.1f} MB"
    }


def read_file_content(file_path: str) -> str:
    """
    读取文件内容（支持txt和md）
    
    Args:
        file_path: 文件路径
    
    Returns:
        文件内容文本
    """
    file = Path(file_path)
    
    if not file.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    ext = file.suffix.lower()
    
    if ext in [".txt", ".md"]:
        return file.read_text(encoding="utf-8")
    elif ext == ".pdf":
        try:
            import PyPDF2
            with open(file, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except ImportError:
            raise ValueError("需要安装 PyPDF2 库来读取 PDF 文件: pip install PyPDF2")
    elif ext == ".docx":
        try:
            import docx
            doc = docx.Document(str(file))
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text
        except ImportError:
            raise ValueError("需要安装 python-docx 库来读取 DOCX 文件: pip install python-docx")
    else:
        raise ValueError(f"不支持的文件类型: {ext}")


@app.post("/api/folder/scan")
async def scan_folder_api(request: FolderScanRequest):
    """
    扫描文件夹，返回文件列表和统计信息
    """
    try:
        logger.info(f"扫描文件夹: {request.folder_path}")
        result = scan_folder(
            request.folder_path,
            request.file_types,
            request.recursive
        )
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"扫描文件夹失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/folder/import")
async def import_folder_api(request: FolderImportRequest):
    """
    扫描文件夹并导入到向量库
    """
    try:
        logger.info(f"开始导入文件夹: {request.folder_path}")
        
        # 扫描文件夹
        scan_result = scan_folder(
            request.folder_path,
            request.file_types,
            request.recursive
        )
        
        if scan_result["total_files"] == 0:
            return {
                "status": "warning",
                "message": "没有找到符合条件的文件",
                "imported_count": 0
            }
        
        # 读取并导入文件
        documents = []
        metadatas = []
        ids = []
        
        for i, file_info in enumerate(scan_result["files"]):
            try:
                content = read_file_content(file_info["path"])
                if content.strip():  # 只导入非空文件
                    documents.append(content)
                    metadatas.append({
                        "source": "folder_import",
                        "file_path": file_info["path"],
                        "file_name": file_info["name"],
                        "file_size": file_info["size"]
                    })
                    ids.append(f"folder_import_{i}")
                    logger.info(f"读取文件: {file_info['name']} ({len(content)} 字符)")
            except Exception as e:
                logger.warning(f"读取文件失败 {file_info['name']}: {e}")
        
        if not documents:
            return {
                "status": "warning",
                "message": "所有文件读取失败或内容为空",
                "imported_count": 0
            }
        
        # 批量添加到向量库
        logger.info(f"正在导入 {len(documents)} 个文档到向量库...")
        add_to_vector_store(documents, metadatas, ids)
        
        logger.info(f"文件夹导入完成: {len(documents)} 个文档")
        
        return {
            "status": "success",
            "message": "文件夹导入成功",
            "imported_count": len(documents),
            "total_files": scan_result["total_files"],
            "folder_path": scan_result["folder_path"]
        }
    
    except Exception as e:
        logger.error(f"导入文件夹失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 文件夹监控 API ==========
class MonitorFolderRequest(BaseModel):
    folder_path: str


class MonitorIntervalRequest(BaseModel):
    interval: int  # 秒


@app.get("/api/monitor/status")
async def get_monitor_status():
    """获取文件夹监控状态"""
    try:
        status = folder_monitor.get_status()
        return {
            "status": "success",
            "data": status
        }
    except Exception as e:
        logger.error(f"获取监控状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/monitor/add_folder")
async def add_monitor_folder(request: MonitorFolderRequest):
    """添加监控文件夹"""
    try:
        success = folder_monitor.add_folder(request.folder_path)
        if success:
            return {
                "status": "success",
                "message": f"已添加监控文件夹: {request.folder_path}",
                "folders": folder_monitor.get_folders()
            }
        else:
            return {
                "status": "failed",
                "message": "添加失败，请检查文件夹路径是否正确"
            }
    except Exception as e:
        logger.error(f"添加监控文件夹失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/monitor/remove_folder")
async def remove_monitor_folder(request: MonitorFolderRequest):
    """移除监控文件夹"""
    try:
        success = folder_monitor.remove_folder(request.folder_path)
        if success:
            return {
                "status": "success",
                "message": f"已移除监控文件夹: {request.folder_path}",
                "folders": folder_monitor.get_folders()
            }
        else:
            return {
                "status": "failed",
                "message": "移除失败，文件夹不在监控列表中"
            }
    except Exception as e:
        logger.error(f"移除监控文件夹失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/monitor/set_interval")
async def set_monitor_interval(request: MonitorIntervalRequest):
    """设置扫描间隔"""
    try:
        folder_monitor.set_scan_interval(request.interval)
        return {
            "status": "success",
            "message": f"扫描间隔已设置为 {request.interval} 秒"
        }
    except Exception as e:
        logger.error(f"设置扫描间隔失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/monitor/enable")
async def enable_monitor():
    """启用文件夹监控"""
    try:
        folder_monitor.enable()
        folder_monitor.start()
        return {
            "status": "success",
            "message": "文件夹监控已启用"
        }
    except Exception as e:
        logger.error(f"启用监控失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/monitor/disable")
async def disable_monitor():
    """禁用文件夹监控"""
    try:
        folder_monitor.disable()
        folder_monitor.stop()
        return {
            "status": "success",
            "message": "文件夹监控已禁用"
        }
    except Exception as e:
        logger.error(f"禁用监控失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/monitor/scan_now")
async def scan_now():
    """立即执行一次扫描"""
    try:
        folder_monitor.scan_all_folders()
        return {
            "status": "success",
            "message": "扫描完成",
            "data": folder_monitor.get_status()
        }
    except Exception as e:
        logger.error(f"立即扫描失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/monitor/files")
async def get_monitored_files():
    """获取已监控的文件列表"""
    try:
        files = []
        for file_path, meta in folder_monitor.file_metadata.items():
            files.append({
                "file_path": meta.file_path,
                "file_name": Path(meta.file_path).name,
                "modified_time": datetime.fromtimestamp(meta.modified_time).isoformat() if meta.modified_time else None,
                "processed_time": datetime.fromtimestamp(meta.processed_time).isoformat() if meta.processed_time else None,
                "file_size": meta.file_size,
                "content_hash": meta.content_hash[:8] + "..."
            })
        
        return {
            "status": "success",
            "data": {
                "total": len(files),
                "files": files
            }
        }
    except Exception as e:
        logger.error(f"获取监控文件列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 启动入口 ==========
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)
