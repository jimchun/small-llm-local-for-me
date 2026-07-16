"""
三级向量数据库 - L1热缓存 + L2主存储 + L3归档(预留)

架构设计：
  L1 (l1_hot_cache): 高频访问数据，LRU淘汰，最多1000条
  L2 (l2_vector_store): 用户文档+知识缓存，最多10000条
  L3 (archive): 预留接口，暂未实现

查询流程：先查L1（毫秒级）→ 再查L2 → 合并去重排序返回
自动提升：L2中被访问>=3次的文档自动提升到L1热缓存
"""
import json
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

import chromadb
from sentence_transformers import SentenceTransformer

from config import CHROMA_PERSIST_DIR, EMBEDDING_MODEL


class VectorStore:
    """三级向量存储"""
    
    # 各层配置
    L1_COLLECTION = "l1_hot_cache"
    L2_COLLECTION = "l2_vector_store"
    L1_MAX_DOCS = 1000
    L2_MAX_DOCS = 10000
    METADATA_FILE = "data/vector_store_metadata.json"
    
    def __init__(self):
        self._embedder = None
        self._client = None
        self._l1 = None  # L1 热缓存 collection
        self._l2 = None  # L2 主存储 collection
        self._initialized = False
        self._metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict:
        """加载元数据"""
        meta_path = Path(self.METADATA_FILE)
        if meta_path.exists():
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "l1_access_stats": {},
            "l2_access_stats": {},
            "total_l1": 0,
            "total_l2": 0,
            "total_queries": 0,
            "total_l1_hits": 0,
            "total_l2_hits": 0,
            "created_at": datetime.now().isoformat(),
        }
    
    def _save_metadata(self):
        """持久化元数据"""
        meta_path = Path(self.METADATA_FILE)
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(self._metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[VectorStore] 保存元数据失败: {e}")
    
    def _ensure_initialized(self):
        """延迟初始化：首次使用时才加载模型和数据库"""
        if self._initialized:
            return
        
        print("[VectorStore] 加载嵌入模型...")
        self._embedder = SentenceTransformer(EMBEDDING_MODEL)
        
        self._client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        
        self._l1 = self._client.get_or_create_collection(
            name=self.L1_COLLECTION,
            metadata={"hnsw:space": "cosine"}
        )
        self._l2 = self._client.get_or_create_collection(
            name=self.L2_COLLECTION,
            metadata={"hnsw:space": "cosine"}
        )
        
        self._metadata["total_l1"] = self._l1.count()
        self._metadata["total_l2"] = self._l2.count()
        
        self._initialized = True
        print(f"[VectorStore] 三级向量库已初始化 | L1: {self._l1.count()}条 | L2: {self._l2.count()}条")
    
    @property
    def embedder(self):
        self._ensure_initialized()
        return self._embedder
    
    @property
    def collection(self):
        """向后兼容：返回L2 collection（旧代码使用）"""
        self._ensure_initialized()
        return self._l2
    
    def _encode(self, texts: List[str]) -> List[List[float]]:
        """生成嵌入向量"""
        return self.embedder.encode(texts, show_progress_bar=False).tolist()
    
    def _encode_query(self, query: str) -> List[float]:
        """生成查询向量"""
        return self.embedder.encode([query])[0].tolist()
    
    # ========== 核心接口 ==========
    
    def add_documents(self, documents: List[str], metadatas: List[Dict] = None, ids: List[str] = None, target_layer: str = "L2"):
        """
        添加文档到指定层
        
        Args:
            documents: 文档文本列表
            metadatas: 元数据列表
            ids: 文档ID列表
            target_layer: "L1" 或 "L2"，默认写入L2
        """
        if not ids:
            ids = [f"doc_{int(time.time()*1000)}_{i}" for i in range(len(documents))]
        
        if not metadatas:
            metadatas = [{} for _ in documents]
        
        now = datetime.now().isoformat()
        for meta in metadatas:
            meta.setdefault("created_at", now)
            meta.setdefault("access_count", 0)
            meta.setdefault("last_accessed", now)
        
        embeddings = self._encode(documents)
        
        if target_layer == "L1":
            self._add_to_l1(documents, embeddings, metadatas, ids)
        else:
            self._add_to_l2(documents, embeddings, metadatas, ids)
        
        print(f"[VectorStore] 添加 {len(documents)} 个文档到 {target_layer}")
    
    def _add_to_l1(self, documents, embeddings, metadatas, ids):
        """添加到L1热缓存，超出上限时LRU淘汰"""
        current_count = self._l1.count()
        needed = current_count + len(documents) - self.L1_MAX_DOCS
        
        if needed > 0:
            self._evict_l1(needed)
        
        self._l1.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        now = datetime.now().isoformat()
        for doc_id in ids:
            self._metadata["l1_access_stats"][doc_id] = {
                "access_count": 0,
                "last_accessed": now,
                "created_at": now
            }
        self._metadata["total_l1"] = self._l1.count()
        self._save_metadata()
    
    def _add_to_l2(self, documents, embeddings, metadatas, ids):
        """添加到L2主存储，超出上限时警告"""
        current_count = self._l2.count()
        if current_count + len(documents) > self.L2_MAX_DOCS:
            print(f"[VectorStore] 警告: L2即将超出上限 ({current_count}+{len(documents)} > {self.L2_MAX_DOCS})")
        
        self._l2.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        now = datetime.now().isoformat()
        for doc_id in ids:
            self._metadata["l2_access_stats"][doc_id] = {
                "access_count": 0,
                "last_accessed": now,
                "created_at": now
            }
        self._metadata["total_l2"] = self._l2.count()
        self._save_metadata()
    
    def _evict_l1(self, count: int):
        """LRU淘汰L1中最近最少访问的文档"""
        if count <= 0:
            return
        
        stats = self._metadata.get("l1_access_stats", {})
        
        sorted_ids = sorted(
            stats.items(),
            key=lambda x: x[1].get("last_accessed", ""),
        )
        
        ids_to_remove = [doc_id for doc_id, _ in sorted_ids[:count]]
        
        if ids_to_remove:
            try:
                self._l1.delete(ids=ids_to_remove)
                for doc_id in ids_to_remove:
                    stats.pop(doc_id, None)
                print(f"[VectorStore] L1 LRU淘汰 {len(ids_to_remove)} 条文档")
            except Exception as e:
                print(f"[VectorStore] L1淘汰失败: {e}")
    
    def search(self, query: str, n_results: int = 3) -> List[Dict]:
        """
        搜索：先查L1再查L2，合并去重排序
        
        Returns:
            [{"content": str, "metadata": dict, "distance": float}, ...]
        """
        query_embedding = self._encode_query(query)
        self._metadata["total_queries"] = self._metadata.get("total_queries", 0) + 1
        
        all_results = []
        
        # 查L1
        l1_count = self._l1.count()
        if l1_count > 0:
            l1_n = min(n_results * 2, l1_count)
            l1_results = self._l1.query(
                query_embeddings=[query_embedding],
                n_results=l1_n
            )
            for i, doc in enumerate(l1_results.get('documents', [[]])[0]):
                metadata = l1_results.get('metadatas', [[]])[0][i] if l1_results.get('metadatas') else {}
                distance = l1_results.get('distances', [[]])[0][i] if l1_results.get('distances') else 0
                doc_id = l1_results.get('ids', [[]])[0][i] if l1_results.get('ids') else ""
                
                self._update_access_stats(doc_id, "l1")
                
                all_results.append({
                    'content': doc,
                    'metadata': {**metadata, '_layer': 'L1', '_doc_id': doc_id},
                    'distance': distance
                })
            
            if all_results:
                self._metadata["total_l1_hits"] = self._metadata.get("total_l1_hits", 0) + 1
        
        # 查L2
        l2_count = self._l2.count()
        if l2_count > 0:
            l2_n = min(n_results * 2, l2_count)
            l2_results = self._l2.query(
                query_embeddings=[query_embedding],
                n_results=l2_n
            )
            for i, doc in enumerate(l2_results.get('documents', [[]])[0]):
                metadata = l2_results.get('metadatas', [[]])[0][i] if l2_results.get('metadatas') else {}
                distance = l2_results.get('distances', [[]])[0][i] if l2_results.get('distances') else 0
                doc_id = l2_results.get('ids', [[]])[0][i] if l2_results.get('ids') else ""
                
                self._update_access_stats(doc_id, "l2")
                
                all_results.append({
                    'content': doc,
                    'metadata': {**metadata, '_layer': 'L2', '_doc_id': doc_id},
                    'distance': distance
                })
            
            if not any(r['metadata'].get('_layer') == 'L1' for r in all_results):
                self._metadata["total_l2_hits"] = self._metadata.get("total_l2_hits", 0) + 1
        
        # 按距离排序（cosine distance越小越相似）
        all_results.sort(key=lambda x: x['distance'])
        
        # 去重（相同doc_id只保留距离最小的）
        seen = set()
        deduped = []
        for r in all_results:
            doc_id = r['metadata'].get('_doc_id', '')
            if doc_id and doc_id not in seen:
                seen.add(doc_id)
                deduped.append(r)
            elif not doc_id:
                deduped.append(r)
        
        result = deduped[:n_results]
        
        # 定期保存元数据（每10次查询保存一次，减少IO）
        if self._metadata["total_queries"] % 10 == 0:
            self._save_metadata()
        
        return result
    
    def _update_access_stats(self, doc_id: str, layer: str):
        """更新访问统计"""
        if not doc_id:
            return
        
        now = datetime.now().isoformat()
        stats_key = f"{layer}_access_stats"
        
        if doc_id in self._metadata.get(stats_key, {}):
            self._metadata[stats_key][doc_id]["access_count"] += 1
            self._metadata[stats_key][doc_id]["last_accessed"] = now
        else:
            self._metadata[stats_key][doc_id] = {
                "access_count": 1,
                "last_accessed": now,
                "created_at": now
            }
    
    # ========== 提升/降级 ==========
    
    def promote_to_l1(self, doc_ids: List[str]):
        """将L2中的文档提升到L1"""
        if not doc_ids:
            return
        
        try:
            l2_data = self._l2.get(ids=doc_ids)
        except Exception as e:
            print(f"[VectorStore] 从L2获取文档失败: {e}")
            return
        
        if not l2_data or not l2_data.get('documents'):
            print(f"[VectorStore] L2中未找到指定文档")
            return
        
        documents = l2_data['documents']
        metadatas = l2_data.get('metadatas', [{} for _ in documents])
        ids = l2_data['ids']
        
        embeddings = self._encode(documents)
        self._add_to_l1(documents, embeddings, metadatas, ids)
        
        print(f"[VectorStore] 提升 {len(doc_ids)} 条文档从L2到L1")
    
    def auto_promote(self, min_access_count: int = 3):
        """
        自动将L2中高频访问的文档提升到L1
        
        Args:
            min_access_count: 最少访问次数阈值
        """
        l2_stats = self._metadata.get("l2_access_stats", {})
        
        candidates = [
            doc_id for doc_id, stats in l2_stats.items()
            if stats.get("access_count", 0) >= min_access_count
        ]
        
        if not candidates:
            return 0
        
        to_promote = candidates[:20]
        self.promote_to_l1(to_promote)
        
        return len(to_promote)
    
    # ========== 统计信息 ==========
    
    def get_stats(self) -> Dict:
        """获取各层统计信息"""
        l1_count = self._l1.count() if self._initialized else 0
        l2_count = self._l2.count() if self._initialized else 0
        
        total_queries = self._metadata.get("total_queries", 0)
        l1_hits = self._metadata.get("total_l1_hits", 0)
        l2_hits = self._metadata.get("total_l2_hits", 0)
        
        hit_rate = (l1_hits / total_queries * 100) if total_queries > 0 else 0
        
        return {
            "l1": {
                "count": l1_count,
                "max_capacity": self.L1_MAX_DOCS,
                "utilization": f"{l1_count / self.L1_MAX_DOCS * 100:.1f}%" if self.L1_MAX_DOCS > 0 else "0%",
            },
            "l2": {
                "count": l2_count,
                "max_capacity": self.L2_MAX_DOCS,
                "utilization": f"{l2_count / self.L2_MAX_DOCS * 100:.1f}%" if self.L2_MAX_DOCS > 0 else "0%",
            },
            "total_documents": l1_count + l2_count,
            "query_stats": {
                "total_queries": total_queries,
                "l1_hits": l1_hits,
                "l2_hits": l2_hits,
                "l1_hit_rate": f"{hit_rate:.1f}%",
            },
            "embedding_model": EMBEDDING_MODEL,
            "persist_dir": CHROMA_PERSIST_DIR,
        }
    
    def get_count(self) -> int:
        """向后兼容：返回总文档数"""
        if not self._initialized:
            return 0
        return self._l1.count() + self._l2.count()
    
    def clear(self, layer: str = "all"):
        """清空指定层"""
        if layer in ("L1", "all"):
            self._client.delete_collection(self.L1_COLLECTION)
            self._l1 = self._client.get_or_create_collection(
                name=self.L1_COLLECTION,
                metadata={"hnsw:space": "cosine"}
            )
            self._metadata["l1_access_stats"] = {}
            self._metadata["total_l1"] = 0
            print("[VectorStore] L1已清空")
        
        if layer in ("L2", "all"):
            self._client.delete_collection(self.L2_COLLECTION)
            self._l2 = self._client.get_or_create_collection(
                name=self.L2_COLLECTION,
                metadata={"hnsw:space": "cosine"}
            )
            self._metadata["l2_access_stats"] = {}
            self._metadata["total_l2"] = 0
            print("[VectorStore] L2已清空")
        
        self._save_metadata()


# ========== 全局单例 ==========
vector_store = VectorStore()


def add_to_vector_store(documents: List[str], metadatas: List[Dict] = None, ids: List[str] = None, target_layer: str = "L2"):
    """添加到向量库的统一接口（向后兼容）"""
    vector_store.add_documents(documents, metadatas, ids, target_layer)


def search_vector_store(query: str, n_results: int = 3) -> List[Dict]:
    """向量搜索的统一接口（向后兼容）"""
    return vector_store.search(query, n_results)
