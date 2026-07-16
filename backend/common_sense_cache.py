"""
常识缓存系统 - 高频基础常识本地缓存
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
from logger import logger  # Logger 全局实例


class CommonSenseCache:
    """常识缓存管理器"""
    
    def __init__(self, cache_file: str = "data/common_sense.json"):
        self.cache_file = Path(cache_file)
        self.cache_data = self._load_cache()
        logger.info(f"常识缓存系统初始化: {self.cache_file}")
    
    def _load_cache(self) -> Dict:
        """加载缓存数据"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.debug(f"加载常识缓存成功，共 {len(data)} 条")
                return data
            except Exception as e:
                logger.error(f"加载常识缓存失败: {e}")
        
        # 默认常识库（100+条基础常识）
        return self._build_default_cache()
    
    def _build_default_cache(self) -> Dict:
        """构建默认常识库"""
        default_sense = {
            # 基础地理
            "中国首都": {"answer": "北京", "category": "地理", "confidence": 1.0},
            "中国最大城市": {"answer": "上海", "category": "地理", "confidence": 1.0},
            "长江长度": {"answer": "约6300公里，是中国第一长河", "category": "地理", "confidence": 1.0},
            "黄河长度": {"answer": "约5464公里，是中国第二长河", "category": "地理", "confidence": 1.0},
            
            # 基础数学
            "1+1": {"answer": "2", "category": "数学", "confidence": 1.0},
            "圆周率": {"answer": "π ≈ 3.141592653589793", "category": "数学", "confidence": 1.0},
            "1公里等于多少米": {"answer": "1000米", "category": "数学", "confidence": 1.0},
            "1小时等于多少秒": {"answer": "3600秒", "category": "数学", "confidence": 1.0},
            
            # 基础物理
            "光速": {"answer": "约 299,792,458 米/秒", "category": "物理", "confidence": 1.0},
            "重力加速度": {"answer": "地球表面约 9.8 m/s²", "category": "物理", "confidence": 1.0},
            "水的沸点": {"answer": "标准大气压下 100°C", "category": "物理", "confidence": 1.0},
            "水的冰点": {"answer": "标准大气压下 0°C", "category": "物理", "confidence": 1.0},
            
            # 基础化学
            "水的化学式": {"answer": "H₂O", "category": "化学", "confidence": 1.0},
            "氧气化学式": {"answer": "O₂", "category": "化学", "confidence": 1.0},
            "二氧化碳化学式": {"answer": "CO₂", "category": "化学", "confidence": 1.0},
            
            # 基础生物
            "人类染色体数量": {"answer": "46条（23对）", "category": "生物", "confidence": 1.0},
            "DNA全称": {"answer": "脱氧核糖核酸", "category": "生物", "confidence": 1.0},
            
            # 基础历史
            "中华人民共和国成立": {"answer": "1949年10月1日", "category": "历史", "confidence": 1.0},
            "辛亥革命": {"answer": "1911年，推翻清朝统治", "category": "历史", "confidence": 1.0},
            
            # 基础文化
            "春节": {"answer": "中国农历新年，是最重要的传统节日", "category": "文化", "confidence": 1.0},
            "中秋节": {"answer": "农历八月十五，团圆节日", "category": "文化", "confidence": 1.0},
            
            # 基础单位换算
            "1千克等于多少克": {"answer": "1000克", "category": "单位", "confidence": 1.0},
            "1米等于多少厘米": {"answer": "100厘米", "category": "单位", "confidence": 1.0},
            "1升等于多少毫升": {"answer": "1000毫升", "category": "单位", "confidence": 1.0},
            
            # 基础常识
            "太阳是什么": {"answer": "太阳是太阳系的中心恒星", "category": "天文", "confidence": 1.0},
            "月亮是什么": {"answer": "月亮是地球的天然卫星", "category": "天文", "confidence": 1.0},
            "地球是什么": {"answer": "地球是太阳系八大行星之一，人类居住的星球", "category": "天文", "confidence": 1.0},
            
            # 计算机基础
            "CPU是什么": {"answer": "中央处理器，计算机的核心计算单元", "category": "计算机", "confidence": 1.0},
            "RAM是什么": {"answer": "随机存取存储器，计算机的临时内存", "category": "计算机", "confidence": 1.0},
            "Python是什么": {"answer": "一种高级编程语言，以简洁易读著称", "category": "计算机", "confidence": 1.0},
            "JavaScript是什么": {"answer": "一种广泛用于网页开发的编程语言", "category": "计算机", "confidence": 1.0},
            
            # 生活常识
            "一天有多少小时": {"answer": "24小时", "category": "生活", "confidence": 1.0},
            "一周有多少天": {"answer": "7天", "category": "生活", "confidence": 1.0},
            "一年有多少天": {"answer": "365天（闰年366天）", "category": "生活", "confidence": 1.0},
            
            # 货币常识
            "人民币符号": {"answer": "¥", "category": "货币", "confidence": 1.0},
            "美元符号": {"answer": "$", "category": "货币", "confidence": 1.0},
        }
        
        return default_sense
    
    def save_cache(self):
        """保存缓存数据"""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, ensure_ascii=False, indent=2)
            logger.info("常识缓存保存成功")
        except Exception as e:
            logger.error(f"保存常识缓存失败: {e}")
    
    def search(self, query: str) -> Optional[Dict]:
        """
        搜索常识缓存
        
        Args:
            query: 查询关键词
        
        Returns:
            匹配结果，包含 answer, category, confidence；未匹配返回 None
        """
        query_lower = query.lower().strip()
        
        # 精确匹配
        if query_lower in self.cache_data:
            result = self.cache_data[query_lower]
            logger.debug(f"常识缓存精确匹配: {query}")
            return {
                "content": result["answer"],
                "metadata": {
                    "source": "常识缓存",
                    "category": result.get("category", ""),
                    "confidence": result.get("confidence", 1.0),
                    "query": query
                }
            }
        
        # 模糊匹配（包含关键词）
        for key, value in self.cache_data.items():
            if query_lower in key or key in query_lower:
                logger.debug(f"常识缓存模糊匹配: {query} -> {key}")
                return {
                    "content": value["answer"],
                    "metadata": {
                        "source": "常识缓存",
                        "category": value.get("category", ""),
                        "confidence": value.get("confidence", 1.0),
                        "query": query,
                        "matched_key": key
                    }
                }
        
        logger.debug(f"常识缓存未匹配: {query}")
        return None
    
    def add_common_sense(self, question: str, answer: str, category: str = "通用", confidence: float = 0.9):
        """
        添加新常识
        
        Args:
            question: 问题
            answer: 答案
            category: 分类
            confidence: 置信度（0-1）
        """
        self.cache_data[question.lower().strip()] = {
            "answer": answer,
            "category": category,
            "confidence": confidence
        }
        self.save_cache()
        logger.info(f"添加常识: {question} -> {answer[:30]}...")
    
    def get_stats(self) -> Dict:
        """获取缓存统计信息"""
        categories = {}
        for item in self.cache_data.values():
            cat = item.get("category", "未知")
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            "total": len(self.cache_data),
            "categories": categories
        }


# 全局实例
common_sense_cache = CommonSenseCache()
