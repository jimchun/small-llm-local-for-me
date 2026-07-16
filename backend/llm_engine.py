"""LLM 推理模块 - Ollama 集成"""
import requests
from typing import List, Dict
from config import OLLAMA_BASE_URL, OLLAMA_MODEL


class LLMInference:
    """本地 LLM 推理引擎"""
    
    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.model = OLLAMA_MODEL
        self._check_connection()
    
    def _check_connection(self):
        """检查 Ollama 连接"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                print(f"[LLM] Ollama 连接成功，模型: {self.model}")
            else:
                print(f"[LLM] 警告: Ollama 返回状态码 {response.status_code}")
        except Exception as e:
            print(f"[LLM] 警告: 无法连接 Ollama - {e}")
    
    def generate(self, prompt: str, context: List[str] = None) -> Dict:
        """生成回答（带检索上下文）"""
        
        # 构建提示词
        if context:
            context_text = "\n\n".join(context)
            system_prompt = f"""你是一个知识助手。请基于以下参考资料回答用户问题。

参考资料：
{context_text}

要求：
1. 仅基于参考资料回答，不要编造信息
2. 如果参考资料中没有相关信息，请明确说明
3. 回答要准确、简洁
4. 在回答末尾标注引用来源

用户问题："""
            full_prompt = f"{system_prompt}\n{prompt}"
        else:
            full_prompt = prompt
        
        try:
            # 调用 Ollama API
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'answer': data.get('response', ''),
                    'model': self.model,
                    'context_used': len(context) if context else 0
                }
            else:
                return {
                    'answer': f"推理引擎返回错误: {response.status_code}",
                    'model': self.model,
                    'context_used': 0
                }
                
        except Exception as e:
            return {
                'answer': f"推理引擎连接失败: {str(e)}",
                'model': self.model,
                'context_used': 0
            }
    
    def chat(self, messages: List[Dict]) -> Dict:
        """对话模式（多轮对话）"""
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'answer': data.get('message', {}).get('content', ''),
                    'model': self.model
                }
            else:
                return {
                    'answer': f"推理引擎返回错误: {response.status_code}",
                    'model': self.model
                }
                
        except Exception as e:
            return {
                'answer': f"推理引擎连接失败: {str(e)}",
                'model': self.model
            }


# 全局实例
llm = LLMInference()


def generate_answer(question: str, context: List[str] = None) -> Dict:
    """生成回答的统一接口"""
    return llm.generate(question, context)
