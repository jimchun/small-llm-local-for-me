"""知识库检索模块 - 维基百科 API 对接"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import re
from config import WIKI_API_URL, WIKI_LANGUAGE


class WikiKnowledgeBase:
    """维基百科知识库"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'LittleLLM/1.0 (Knowledge Assistant)'
        })
    
    def search(self, query: str, limit: int = 3) -> List[Dict]:
        """搜索维基百科词条"""
        try:
            # 搜索词条
            search_params = {
                'action': 'query',
                'list': 'search',
                'srsearch': query,
                'srlimit': limit,
                'format': 'json',
                'utf8': 1
            }
            
            search_response = self.session.get(WIKI_API_URL, params=search_params, timeout=10)
            search_data = search_response.json()
            
            results = []
            search_hits = search_data.get('query', {}).get('search', [])
            
            for hit in search_hits:
                title = hit['title']
                # 获取词条摘要
                summary = self._get_page_summary(title)
                if summary:
                    results.append({
                        'title': title,
                        'summary': summary,
                        'url': f"https://zh.wikipedia.org/wiki/{title}",
                        'source': '维基百科'
                    })
            
            return results
            
        except Exception as e:
            print(f"[WikiKB] 搜索失败: {e}")
            return []
    
    def _get_page_summary(self, title: str, sentences: int = 3) -> str:
        """获取词条摘要"""
        try:
            params = {
                'action': 'query',
                'titles': title,
                'prop': 'extracts',
                'exsentences': sentences,
                'explaintext': 1,
                'format': 'json',
                'utf8': 1
            }
            
            response = self.session.get(WIKI_API_URL, params=params, timeout=10)
            data = response.json()
            
            pages = data.get('query', {}).get('pages', {})
            for page_id, page_data in pages.items():
                extract = page_data.get('extract', '')
                if extract:
                    # 清理文本
                    extract = re.sub(r'\s+', ' ', extract).strip()
                    return extract
            
            return ""
            
        except Exception as e:
            print(f"[WikiKB] 获取摘要失败: {e}")
            return ""
    
    def get_full_content(self, title: str) -> str:
        """获取完整词条内容"""
        try:
            params = {
                'action': 'query',
                'titles': title,
                'prop': 'extracts',
                'explaintext': 1,
                'format': 'json',
                'utf8': 1
            }
            
            response = self.session.get(WIKI_API_URL, params=params, timeout=10)
            data = response.json()
            
            pages = data.get('query', {}).get('pages', {})
            for page_id, page_data in pages.items():
                return page_data.get('extract', '')
            
            return ""
            
        except Exception as e:
            print(f"[WikiKB] 获取完整内容失败: {e}")
            return ""


# 全局实例
wiki_kb = WikiKnowledgeBase()


def search_knowledge(query: str, limit: int = 3) -> List[Dict]:
    """统一的知识库搜索接口"""
    return wiki_kb.search(query, limit)
