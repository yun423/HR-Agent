"""
通用 LLM 调用服务：
    封装 OpenAI 兼容客户端，提供普通回复、流式回复、生成embedding、文本摘要、生成建议等能力。
    其他服务不直接拼LLM API，而是通过它统一调用。
"""
import logging
import httpx
import asyncio
import openai
from typing import List, Dict, Any, Optional, AsyncGenerator
# 移除了LangChain导入以避免兼容性问题

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """LLM交互服务"""

    def __init__(self):
        # 使用配置的LLM初始化OpenAI客户端
        llm_api_key = getattr(settings, 'LLM_API_KEY', None) or settings.LLM_API_KEY
        llm_base_url = getattr(settings, 'LLM_BASE_URL', None) or 'https://dashscope.aliyuncs.com/compatible-mode/v1'
        self.llm_model = getattr(settings, 'LLM_MODEL', 'qwen-max')

        # 传递base_url，除非是默认的OpenAI URL
        client_kwargs = {'api_key': llm_api_key}
        if llm_base_url != 'https://api.openai.com/v1':
            client_kwargs['base_url'] = llm_base_url

        self.client = openai.AsyncOpenAI(**client_kwargs)

        # 对于嵌入，我们将使用自定义实现，因为我们有不同的API
        self.embedding_api_key = settings.EMBEDDING_API_KEY or settings.LLM_API_KEY
        self.embedding_base_url = settings.EMBEDDING_BASE_URL or 'https://dashscope.aliyuncs.com/compatible-mode/v1'
        self.embedding_model = settings.EMBEDDING_MODEL or 'text-embedding-v1'

        # 嵌入配置只在真正调用 generate_embedding 时使用，初始化聊天模型时不输出 info 日志，避免误以为 Agent 规划调用了向量模型。
        logger.debug(f"Embedding config - Base URL: {self.embedding_base_url}")
        logger.debug(f"Embedding config - Model: {self.embedding_model}")

        # HR Agent 当前产品能力提示：避免普通聊天夸大成通用 HR 咨询助手
        self.system_prompt = """你是招聘场景的 HR Agent 助手，不是通用人力资源政策/薪酬/绩效咨询助手。

        你当前能帮助用户完成：
        - 生成岗位 JD，并生成简历评分标准
        - 上传简历后，基于指定 JD 进行简历评分/筛选
        - 基于已评分候选人生成面试计划
        - 基于上传文档生成笔试试卷；如果有当前面试方案，可按约 8:2 结合文档和面试方案出题
        - 生成邮件通知草稿，但不会自动发送
        - 通过聊天删除已生成的 JD、简历评分记录、面试方案、试卷

        如果用户询问“你能做什么/有哪些能力”，只介绍以上能力。
        不要宣称可以处理员工薪酬福利、绩效管理、劳动法合规、员工关系冲突等当前产品未接入的泛 HR 咨询能力。
        如果用户提出超出当前工具范围的需求，礼貌说明暂不支持，并建议转为当前支持的招聘闭环任务。"""

    async def generate_response(
        self,
        message: str,
        conversation_history: List[Dict[str, str]] = None,
        context: Optional[str] = None
    ) -> str:
        """
        使用聊天模型生成响应
        """
        try:
            messages = [{"role": "system", "content": self.system_prompt}]

            # 添加对话历史
            if conversation_history:
                for msg in conversation_history[-10:]:  # 保留最后10条消息
                    messages.append({"role": msg["role"], "content": msg["content"]})

            # 如有提供，添加上下文
            if context:
                context_message = f"相关上下文: {context}\n\n用户问题: {message}"
                messages.append({"role": "user", "content": context_message})
            else:
                messages.append({"role": "user", "content": message})

            response = await self.client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"生成响应时出错: {e}")
            raise

    async def stream_response(
        self,
        message: str,
        conversation_history: List[Dict[str, str]] = None,
        context: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        生成流式响应
        """
        try:
            messages = [{"role": "system", "content": self.system_prompt}]

            # 添加对话历史
            if conversation_history:
                for msg in conversation_history[-10:]:
                    messages.append({"role": msg["role"], "content": msg["content"]})

            # 如有提供，添加上下文
            if context:
                context_message = f"相关上下文: {context}\n\n用户问题: {message}"
                messages.append({"role": "user", "content": context_message})
            else:
                messages.append({"role": "user", "content": message})

            # 流式传输响应
            stream = await self.client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
                stream=True
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"流式传输响应时出错: {e}")
            raise

    async def generate_embedding(self, text: str) -> List[float]:
        """
        使用配置的嵌入API为文本生成嵌入
        """
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {self.embedding_api_key}",
                    "Content-Type": "application/json"
                }

                data = {
                    "model": self.embedding_model,
                    "input": text
                }

                response = await client.post(
                    f"{self.embedding_base_url}/embeddings",
                    headers=headers,
                    json=data,
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                    return result["data"][0]["embedding"]
                else:
                    logger.error(f"嵌入API错误: {response.status_code} - {response.text}")
                    raise Exception(f"嵌入API错误: {response.status_code}")

        except Exception as e:
            logger.error(f"生成嵌入时出错: {e}")
            raise


    async def summarize_text(self, text: str, max_length: int = 200) -> str:
        """
        使用LLM总结文本
        """
        try:
            prompt = f"""请用不超过{max_length}个词提供以下文本的简洁摘要：

{text}

摘要:"""

            response = await self.client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=max_length * 2  # 为令牌留出一些缓冲区
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"总结文本时出错: {e}")
            raise

    async def generate_suggestions(self, query: str, context: str = "") -> List[str]:
        """
        根据输入生成查询建议
        """
        try:
            prompt = f"""基于以下HR相关查询，建议5个用户可能想要询问的相关问题：

查询: {query}
上下文: {context}

提供5个简短、相关的问题（每行一个）："""

            response = await self.client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=300
            )
            suggestions_text = response.choices[0].message.content.strip()

            # 解析建议
            suggestions = [s.strip() for s in suggestions_text.split("\n") if s.strip()]
            return suggestions[:5]

        except Exception as e:
            logger.error(f"生成建议时出错: {e}")
            raise
