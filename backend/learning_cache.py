"""
动态学习缓存系统 - 高频查询自动沉淀到本地缓存
当用户重复提问时，优先从本地缓存返回，减少联网检索
"""
import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from logger import logger


class LearningCache:
    """动态学习缓存管理器"""
    
    def __init__(self, cache_file: str = "data/learning_cache.json"):
        """
        Args:
            cache_file: 缓存文件路径
        """
        self.cache_file = Path(cache_file)
        self.cache_data = self._load_cache()
        
        # 缓存配置
        self.max_entries = 1000  # 最大缓存条目
        self.min_hit_count = 3   # 最少命中次数才沉淀
        self.ttl_days = 30       # 缓存有效期（天）
        
        logger.info(f"动态学习缓存系统初始化: {self.cache_file}, 当前 {len(self.cache_data)} 条")
    
    def _load_cache(self) -> Dict:
        """加载缓存数据"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # 清理过期条目
                data = self._cleanup_expired(data)
                return data
            except Exception as e:
                logger.error(f"加载学习缓存失败: {e}")
        
        return {}
    
    def _cleanup_expired(self, data: Dict) -> Dict:
        """清理过期缓存"""
        now = datetime.now().timestamp()
        ttl_seconds = self.ttl_days * 24 * 3600
        
        cleaned = {}
        for key, item in data.items():
            created_at = item.get('created_at', 0)
            if now - created_at < ttl_seconds:
                cleaned[key] = item
        
        expired_count = len(data) - len(cleaned)
        if expired_count > 0:
            logger.debug(f"清理过期缓存: {expired_count} 条")
        
        return cleaned
    
    def save_cache(self):
        """保存缓存数据"""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, ensure_ascii=False, indent=2)
            logger.debug(f"学习缓存保存成功: {len(self.cache_data)} 条")
        except Exception as e:
            logger.error(f"保存学习缓存失败: {e}")
    
    def query(self, question: str) -> Optional[Dict]:
        """
        查询学习缓存
        
        Args:
            question: 用户问题
        
        Returns:
            匹配的缓存结果，包含 answer, sources, hit_count；未命中返回 None
        """
        key = self._normalize_key(question)
        
        if key not in self.cache_data:
            return None
        
        item = self.cache_data[key]
        
        # 检查是否过期
        now = datetime.now().timestamp()
        ttl_seconds = self.ttl_days * 24 * 3600
        if now - item.get('created_at', 0) > ttl_seconds:
            # 过期，删除
            del self.cache_data[key]
            self.save_cache()
            return None
        
        # 更新命中统计
        item['hit_count'] = item.get('hit_count', 0) + 1
        item['last_hit'] = now
        
        logger.info(f"学习缓存命中: {question} (第{item['hit_count']}次)")
        
        return {
            'answer': item['answer'],
            'sources': item.get('sources', []),
            'intent': item.get('intent', 'B'),
            'hit_count': item['hit_count'],
            'from_cache': True
        }
    
    def record(self, question: str, answer: str, sources: Optional[List[Dict]] = None, intent: str = 'B'):
        """
        记录一次查询结果（用于后续沉淀）
        
        Args:
            question: 用户问题
            answer: 生成的回答
            sources: 引用的知识源
            intent: 意图分类（A/B/C）
        """
        key = self._normalize_key(question)
        now = datetime.now().timestamp()
        
        if key in self.cache_data:
            # 已存在，增加查询次数
            item = self.cache_data[key]
            item['query_count'] = item.get('query_count', 0) + 1
            item['last_query'] = now
            item['answer'] = answer  # 更新最新回答
            item['sources'] = sources or item.get('sources', [])
        else:
            # 新记录
            self.cache_data[key] = {
                'question': question,
                'answer': answer,
                'sources': sources or [],
                'intent': intent,
                'query_count': 1,
                'hit_count': 0,  # 缓存命中次数
                'created_at': now,
                'last_query': now
            }
        
        # 检查是否需要沉淀（查询次数达到阈值）
        if self.cache_data[key]['query_count'] >= self.min_hit_count:
            logger.info(f"学习缓存沉淀: {question} (查询{self.cache_data[key]['query_count']}次)")
        
        # 限制缓存大小
        if len(self.cache_data) > self.max_entries:
            self._evict_oldest()
        
        self.save_cache()
    
    def _evict_oldest(self):
        """淘汰最旧的缓存条目"""
        # 按最后查询时间排序
        sorted_items = sorted(
            self.cache_data.items(),
            key=lambda x: x[1].get('last_query', 0)
        )
        
        # 删除最旧的 10%
        evict_count = max(1, len(sorted_items) // 10)
        for key, _ in sorted_items[:evict_count]:
            del self.cache_data[key]
        
        logger.debug(f"淘汰旧缓存: {evict_count} 条")
    
    def _normalize_key(self, question: str) -> str:
        """标准化问题键名"""
        return question.lower().strip().replace('？', '').replace('?', '')
    
    def get_pending_deposition(self) -> List[Dict]:
        """
        获取待沉淀的高频查询
        （查询次数达到阈值但尚未沉淀的）
        
        Returns:
            待沉淀的查询列表
        """
        pending = []
        for key, item in self.cache_data.items():
            if item.get('query_count', 0) >= self.min_hit_count and item.get('hit_count', 0) == 0:
                pending.append({
                    'question': item['question'],
                    'answer': item['answer'],
                    'query_count': item['query_count']
                })
        
        return pending
    
    def promote_to_common_sense(self, question: str, answer: str, category: str = "学习沉淀"):
        """
        将学习缓存提升为常识缓存
        
        Args:
            question: 问题
            answer: 答案
            category: 分类
        """
        # 导入常识缓存
        try:
            from common_sense_cache import common_sense_cache
            common_sense_cache.add_common_sense(question, answer, category, confidence=0.85)
            
            # 标记为已沉淀
            key = self._normalize_key(question)
            if key in self.cache_data:
                self.cache_data[key]['promoted'] = True
                self.save_cache()
            
            logger.info(f"学习缓存提升为常识: {question}")
        except Exception as e:
            logger.error(f"提升学习缓存失败: {e}")
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        total_queries = sum(item.get('query_count', 0) for item in self.cache_data.values())
        total_hits = sum(item.get('hit_count', 0) for item in self.cache_data.values())
        pending_count = len(self.get_pending_deposition())
        
        return {
            'total_entries': len(self.cache_data),
            'total_queries': total_queries,
            'total_hits': total_hits,
            'pending_deposition': pending_count,
            'hit_rate': round(total_hits / total_queries, 3) if total_queries > 0 else 0
        }


# 全局实例
learning_cache = LearningCache()
