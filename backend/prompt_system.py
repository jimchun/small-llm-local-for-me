"""
强制引用系统 - 通过 Prompt 约束防止幻觉
"""
from typing import List, Dict, Optional
from logger import logger  # Logger 全局实例


class PromptSystem:
    """强制引用 Prompt 系统"""
    
    @staticmethod
    def build_retrieval_prompt(question: str, context: List[Dict]) -> str:
        """
        构建检索 Prompt，强制要求引用来源
        
        Args:
            question: 用户问题
            context: 检索到的上下文列表，每项包含 {content, metadata}
        
        Returns:
            格式化后的 Prompt 字符串
        """
        # 格式化上下文
        context_text = ""
        for i, item in enumerate(context, 1):
            content = item.get('content', '')
            metadata = item.get('metadata', {})
            source = metadata.get('source', '未知来源')
            title = metadata.get('title', '')
            
            context_text += f"\n[来源{i}] {source}"
            if title:
                context_text += f" - {title}"
            context_text += f"\n{content}\n"
        
        # 构建强制引用 Prompt
        prompt = f"""你是一个严格基于事实的问答助手。请遵循以下规则回答用户问题：

【核心规则】
1. 只使用下面提供的参考资料回答问题
2. 每个事实性陈述必须标注来源（如"[来源1]"）
3. 如果参考资料中没有相关信息，明确说"根据提供的资料，无法回答这个问题"
4. 禁止使用自己的知识或推测
5. 如果多个来源有冲突，指出差异并说明

【参考资料】
{context_text}

【用户问题】
{question}

【回答要求】
- 所有事实必须标注来源
- 结构清晰，分点回答
- 如果无法回答，明确说明原因

请回答："""
        
        logger.info(f"构建检索 Prompt，上下文数量: {len(context)}")
        return prompt
    
    @staticmethod
    def build_no_context_prompt(question: str) -> str:
        """
        构建无上下文时的兜底 Prompt
        
        Args:
            question: 用户问题
        
        Returns:
            格式化后的 Prompt 字符串
        """
        prompt = f"""你是一个严格基于事实的问答助手。

当前没有检索到相关资料。

请遵循以下规则：
1. 如果没有参考资料，明确说"根据提供的资料，无法回答这个问题"
2. 禁止使用自己的知识或推测
3. 可以建议用户换个角度提问或提供更多背景

【用户问题】
{question}

请回答："""
        
        logger.info("构建无上下文 Prompt")
        return prompt
    
    @staticmethod
    def build_intent_classification_prompt(question: str) -> str:
        """
        构建意图分类 Prompt（A/B/C 三分类）
        
        A: 个人记忆/私有文档
        B: 公共知识/百科事实
        C: 需要结合公共知识和用户情况
        
        Args:
            question: 用户问题
        
        Returns:
            用于意图分类的 Prompt
        """
        prompt = f"""请判断以下问题属于哪个类别，只返回字母 A、B 或 C：

A: 涉及个人记忆、私有文档（如"我之前提到的项目"、"我的笔记"）
B: 涉及公共知识、百科事实（如"量子力学是什么"、"Python 语法"）
C: 需要结合公共知识和用户情况（如"根据我的背景，该选什么"）

问题：{question}

类别（只返回 A、B 或 C）："""
        
        logger.debug(f"构建意图分类 Prompt: {question[:50]}...")
        return prompt
    
    @staticmethod
    def parse_classification_result(result: str) -> str:
        """
        解析意图分类结果
        
        Args:
            result: LLM 返回的分类结果
        
        Returns:
            标准化的类别：'A', 'B', 或 'C'
        """
        result = result.strip().upper()
        
        # 提取第一个出现的 A/B/C
        for char in result:
            if char in ['A', 'B', 'C']:
                logger.debug(f"意图分类结果: {char}")
                return char
        
        # 默认返回 B（公共知识）
        logger.warning(f"无法解析分类结果 '{result}'，默认使用 B")
        return 'B'


class PromptBuilder:
    """Prompt 构建器（main.py 需要的接口）"""
    
    def _build_context_section(self, context: list) -> str:
        """构建参考资料部分"""
        if not context:
            return "【参考资料】\n无"
        
        lines = ["【参考资料】"]
        for i, item in enumerate(context, 1):
            content = item.get("content", "")
            metadata = item.get("metadata", {})
            source = metadata.get("source", "未知来源")
            title = metadata.get("title", "")
            lines.append(f"\n[来源{i}] {source}")
            if title:
                lines[-1] += f" - {title}"
            lines.append(content)
        return "\n".join(lines)
    
    def _build_profile_section(self, user_profile: str) -> str:
        """构建用户画像部分"""
        if not user_profile:
            return ""
        return f"【用户画像】\n{user_profile}"
    
    def build_strict_prompt(self, question: str, context: list, user_profile: str = "") -> str:
        """
        构建强制引用 Prompt
        
        Args:
            question: 用户问题
            context: 上下文列表，每项包含 content 和 metadata
            user_profile: 用户画像文本
        
        Returns:
            完整的 Prompt 字符串
        """
        context_text = self._build_context_section(context)
        profile_section = self._build_profile_section(user_profile) if user_profile else ""
        
        prompt = f"""你是一个严格基于事实的问答助手。请遵循以下规则回答用户问题：

{profile_section}

{context_text}

【回答规则】
1. 只使用上面提供的参考资料回答问题
2. 每个事实性陈述必须标注来源（如"[来源1]"）
3. 如果参考资料中没有相关信息，明确说"根据提供的资料，无法回答这个问题"
4. 禁止使用自己的知识或推测
5. 如果多个来源有冲突，指出差异并说明

【用户问题】
{question}

请回答："""
        
        return prompt
    
    def build_no_context_prompt(self, question: str, user_profile: str = "") -> str:
        """
        构建无上下文时的兜底 Prompt
        
        Args:
            question: 用户问题
            user_profile: 用户画像文本
        
        Returns:
            完整的 Prompt 字符串
        """
        prompt = PromptSystem.build_no_context_prompt(question)
        profile_section = self._build_profile_section(user_profile) if user_profile else ""
        if profile_section:
            prompt = f"{profile_section}\n\n{prompt}"
        return prompt
    
    def build_intent_classification_prompt(self, question: str) -> str:
        """
        构建意图分类 Prompt
        
        Args:
            question: 用户问题
        
        Returns:
            用于意图分类的 Prompt
        """
        return PromptSystem.build_intent_classification_prompt(question)
    
    def parse_intent_result(self, result: str) -> str:
        """
        解析意图分类结果
        
        Args:
            result: LLM 返回的分类结果
        
        Returns:
            标准化的类别：'A', 'B', 或 'C'
        """
        return PromptSystem.parse_classification_result(result)
