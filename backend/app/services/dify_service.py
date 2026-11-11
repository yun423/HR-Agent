"""
Dify 工作流调用服务:
    DifyService 根据不同 workflow type 调用 Dify API，支持同步调用和流式调用。
    它负责拼请求、带 conversation_id、处理 Dify 返回事件、提取 answer/data/error 等内容，是项目连接 Dify 工作流的统一入口。
"""

import json
import uuid
from typing import Dict, Any, AsyncGenerator, Optional
import httpx
from fastapi import HTTPException
from app.core.config import settings
from app.core.logging import logger


class DifyService:
    """用于与Dify工作流交互的服务"""

    def __init__(self):
        self.base_url = settings.DIFY_BASE_URL
        self.api_key = settings.DIFY_API_KEY
        self.user_id = settings.DIFY_USER_ID

        if not self.api_key:
            raise ValueError("DIFY_API_KEY是必需的但未配置")

    async def call_workflow_stream(
        self,
        workflow_type: int,
        query: str,
        conversation_id: Optional[str] = None,
        additional_inputs: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        调用Dify工作流并流式响应

        Args:
            workflow_type: 工作流类型 (1=JD生成, 2=简历评价, 等)
            query: 用户查询/提示
            conversation_id: 可选的对话ID以提供上下文
            additional_inputs: 额外的输入参数

        Yields:
            流式响应数据
        """
        try:
            # 准备请求数据
            inputs = {"type": workflow_type}
            if additional_inputs:
                inputs.update(additional_inputs)

            request_data = {
                "inputs": inputs,
                "query": query,
                "response_mode": "streaming",
                "conversation_id": conversation_id or "",
                "user": self.user_id
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            logger.info(f"调用Dify工作流类型 {workflow_type}，查询: {query[:100]}...")

            # 向Dify发起流式请求
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat-messages",
                    headers=headers,
                    json=request_data
                ) as response:

                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"Dify API错误: {response.status_code} - {error_text}")
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=f"Dify API错误: {error_text.decode()}"
                        )

                    # 流式传输响应
                    async for chunk in response.aiter_lines():
                        if chunk:
                            chunk = chunk.strip()

                            # 跳过SSE控制行和心跳包，避免被前端误当作正文
                            lowered = chunk.lower()
                            if (
                                lowered.startswith("event:")
                                or lowered.startswith("id:")
                                or lowered.startswith("retry:")
                                or lowered == "ping"
                                or lowered == "event: ping"
                            ):
                                continue

                            # 如果存在'data: '前缀则移除
                            if chunk.startswith("data: "):
                                chunk = chunk[6:].strip()

                            # 跳过空行和[DONE]标记
                            if not chunk or chunk == "[DONE]":
                                continue

                            try:
                                # 解析JSON块
                                data = json.loads(chunk)
                                if str(data.get("event") or "").lower() == "ping":
                                    continue
                                yield chunk
                            except json.JSONDecodeError:
                                # 非JSON正文才透传，SSE控制内容在上面已过滤
                                yield chunk

        except httpx.TimeoutException:
            logger.error("Dify API请求超时")
            raise HTTPException(status_code=504, detail="Dify API请求超时")
        except httpx.RequestError as e:
            logger.error(f"Dify API请求错误: {str(e)}")
            raise HTTPException(status_code=503, detail=f"Dify API请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"Dify工作流调用中出现意外错误: {str(e)}")
            raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")

    async def call_workflow_sync(
        self,
        workflow_type: int,
        query: str,
        conversation_id: Optional[str] = None,
        additional_inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        调用Dify工作流并同步响应

        Args:
            workflow_type: 工作流类型
            query: 用户查询/提示
            conversation_id: 可选的对话ID
            additional_inputs: 额外的输入参数

        Returns:
            完整的响应数据
        """
        try:
            inputs = {"type": workflow_type}
            if additional_inputs:
                inputs.update(additional_inputs)

            request_data = {
                "inputs": inputs,
                "query": query,
                "response_mode": "blocking",
                "conversation_id": conversation_id or "",
                "user": self.user_id
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            logger.info(f"调用Dify工作流类型 {workflow_type} (同步)，查询: {query[:100]}...")

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat-messages",
                    headers=headers,
                    json=request_data
                )

                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"Dify API错误: {response.status_code} - {error_text}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Dify API错误: {error_text}"
                    )

                return response.json()

        except httpx.TimeoutException:
            logger.error("Dify API请求超时")
            raise HTTPException(status_code=504, detail="Dify API请求超时")
        except httpx.RequestError as e:
            logger.error(f"Dify API请求错误: {str(e)}")
            raise HTTPException(status_code=503, detail=f"Dify API请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"Dify工作流调用中出现意外错误: {str(e)}")
            raise HTTPException(status_code=500, detail=f"内部服务器错误: {str(e)}")
