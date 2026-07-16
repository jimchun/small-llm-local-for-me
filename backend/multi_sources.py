"""
多知识源系统 - 支持多个数据源并自动权重分配
"""
import requests
from typing import List, Dict, Optional
from abc import ABC, abstractmethod
from logger import logger  # Logger 全局实例


class KnowledgeSource(ABC):
    """知识源抽象基类"""
    
    def __init__(self, name: str, weight: float = 1.0):
        """
        Args:
            name: 知识源名称
            weight: 权重（0-1之间）
        """
        self.name = name
        self.weight = weight
        self.enabled = True
    
    @abstractmethod
    def search(self, query: str, limit: int = 3) -> List[Dict]:
        """
        搜索知识源
        
        Args:
            query: 搜索关键词
            limit: 返回结果数量限制
        
        Returns:
            搜索结果列表，每项包含 {content, metadata}
        """
        pass
    
    def is_available(self) -> bool:
        """检查知识源是否可用"""
        return self.enabled


class WikipediaSource(KnowledgeSource):
    """维基百科知识源（权威性：高）"""
    
    def __init__(self):
        super().__init__("维基百科", weight=0.9)
        self.api_url = "https://zh.wikipedia.org/w/api.php"
    
    def search(self, query: str, limit: int = 3) -> List[Dict]:
        """搜索维基百科"""
        try:
            # 搜索 API
            search_params = {
                'action': 'query',
                'list': 'search',
                'srsearch': query,
                'srlimit': limit,
                'format': 'json'
            }
            
            response = requests.get(self.api_url, params=search_params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            results = []
            search_results = data.get('query', {}).get('search', [])
            
            # 获取摘要
            for item in search_results[:limit]:
                title = item.get('title', '')
                pageid = item.get('pageid', '')
                
                # 获取摘要
                summary = self._get_summary(title)
                if summary:
                    results.append({
                        'content': summary,
                        'metadata': {
                            'source': self.name,
                            'title': title,
                            'url': f"https://zh.wikipedia.org/wiki/{title}",
                            'authority': 'high'
                        }
                    })
            
            logger.info(f"维基百科搜索 '{query}'，返回 {len(results)} 条结果")
            return results
            
        except Exception as e:
            logger.error(f"维基百科搜索失败: {e}")
            return []
    
    def _get_summary(self, title: str) -> Optional[str]:
        """获取词条摘要"""
        try:
            params = {
                'action': 'query',
                'titles': title,
                'prop': 'extracts',
                'exintro': True,
                'explaintext': True,
                'format': 'json'
            }
            
            response = requests.get(self.api_url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            pages = data.get('query', {}).get('pages', {})
            for page_id, page_data in pages.items():
                extract = page_data.get('extract', '')
                if extract:
                    # 截取前500字符
                    return extract[:500]
            
            return None
            
        except Exception as e:
            logger.error(f"获取维基百科摘要失败: {e}")
            return None


class BaiduBaikeSource(KnowledgeSource):
    """百度百科知识源（权威性：中）"""
    
    def __init__(self):
        super().__init__("百度百科", weight=0.7)
    
    def search(self, query: str, limit: int = 3) -> List[Dict]:
        """搜索百度百科（使用 Wikipedia API 替代，因为百度百科无官方API）"""
        try:
            # 百度百科没有官方 API，这里使用中文 Wikipedia 作为替代
            # 实际生产环境可以考虑接入其他中文知识源（如搜狗百科、360百科）
            api_url = "https://zh.wikipedia.org/w/api.php"
            
            # 搜索 API
            search_params = {
                'action': 'query',
                'list': 'search',
                'srsearch': query,
                'srlimit': limit,
                'format': 'json'
            }
            
            response = requests.get(api_url, params=search_params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            results = []
            search_results = data.get('query', {}).get('search', [])
            
            # 获取摘要
            for item in search_results[:limit]:
                title = item.get('title', '')
                pageid = item.get('pageid', '')
                
                # 获取摘要
                summary = self._get_summary(api_url, title)
                if summary:
                    results.append({
                        'content': summary,
                        'metadata': {
                            'source': self.name,
                            'title': title,
                            'url': f"https://zh.wikipedia.org/wiki/{title}",
                            'authority': 'medium'
                        }
                    })
            
            logger.info(f"百度百科(替代)搜索 '{query}'，返回 {len(results)} 条结果")
            return results
            
        except Exception as e:
            logger.error(f"百度百科搜索失败: {e}")
            return []
    
    def _get_summary(self, api_url: str, title: str) -> Optional[str]:
        """获取词条摘要"""
        try:
            params = {
                'action': 'query',
                'titles': title,
                'prop': 'extracts',
                'exintro': True,
                'explaintext': True,
                'format': 'json'
            }
            
            response = requests.get(api_url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            pages = data.get('query', {}).get('pages', {})
            for page_id, page_data in pages.items():
                extract = page_data.get('extract', '')
                if extract:
                    # 截取前500字符
                    return extract[:500]
            
            return None
            
        except Exception as e:
            logger.error(f"获取百度百科摘要失败: {e}")
            return None


class LocalVectorStoreSource(KnowledgeSource):
    """本地向量库知识源（权威性：取决于数据来源）"""
    
    def __init__(self, vector_store):
        super().__init__("本地知识库", weight=0.8)
        self.vector_store = vector_store
    
    def search(self, query: str, limit: int = 3) -> List[Dict]:
        """搜索本地向量库"""
        try:
            if not self.vector_store:
                return []
            
            results = self.vector_store.search(query, top_k=limit)
            
            formatted_results = []
            for item in results:
                formatted_results.append({
                    'content': item.get('content', ''),
                    'metadata': {
                        'source': self.name,
                        'title': item.get('metadata', {}).get('title', '未命名'),
                        'authority': 'medium'
                    }
                })
            
            logger.info(f"本地知识库搜索 '{query}'，返回 {len(formatted_results)} 条结果")
            return formatted_results
            
        except Exception as e:
            logger.error(f"本地知识库搜索失败: {e}")
            return []


class MultiSourceManager:
    """多知识源管理器"""
    
    def __init__(self):
        self.sources: List[KnowledgeSource] = []
        logger.info("多知识源管理器初始化")
    
    def add_source(self, source: KnowledgeSource):
        """添加知识源"""
        self.sources.append(source)
        logger.info(f"添加知识源: {source.name} (权重: {source.weight})")
    
    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """
        从所有启用的知识源搜索并按权重融合
        
        Args:
            query: 搜索关键词
            limit: 返回结果总数限制
        
        Returns:
            按权重排序的融合结果
        """
        all_results = []
        
        # 从所有启用的知识源搜索
        for source in self.sources:
            if source.is_available():
                try:
                    # 根据权重调整每个源的返回数量
                    source_limit = max(1, int(limit * source.weight))
                    results = source.search(query, limit=source_limit)
                    
                    # 为每个结果添加权重分数
                    for result in results:
                        result['_weight_score'] = source.weight
                        all_results.append(result)
                        
                except Exception as e:
                    logger.error(f"知识源 {source.name} 搜索异常: {e}")
        
        # 按权重排序
        all_results.sort(key=lambda x: x.get('_weight_score', 0), reverse=True)
        
        # 限制总数
        final_results = all_results[:limit]
        
        # 清理内部字段
        for result in final_results:
            result.pop('_weight_score', None)
        
        logger.info(f"多知识源融合搜索完成，共 {len(final_results)} 条结果")
        return final_results


# 全局实例
multi_source_manager = MultiSourceManager()
