"""End-to-end acceptance tests for document parsing, RAG, and resume scoring."""

from __future__ import annotations

import argparse
import asyncio
import json
import mimetypes
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from langchain_core.documents import Document as LangChainDocument
from langchain_postgres import PGVector
from sqlalchemy import update

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.document import Document
from app.services.embedding_service import get_embedding_service
from app.utils.text_utils import extract_text_content


PROJECT_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_DIR = PROJECT_ROOT / "测试文档"
RESUME_DIR = PROJECT_ROOT / "简历评估测试"
DEFAULT_OUTPUT = PROJECT_ROOT / "docs" / "acceptance_test_results_2026-09-10.json"
JD_TITLE = "验收测试-AI/Java软件工程师"

KNOWLEDGE_QUESTIONS = [
    {
        "filename": "03.1 RAG应用评估技能和工具.md",
        "question": "RAG 评估中上下文精度通常有哪两种定义方式？",
        "reference": "一种是看相关上下文是否出现在结果前面，即位置；另一种是相关信息数量占上下文总信息数量的比例。",
        "keywords": ["位置", "比例"],
    },
    {
        "filename": "《自然语言处理》完整复习题库.md",
        "question": "Transformer 相比 RNN 为什么更适合并行计算？",
        "reference": "Transformer 完全基于自注意力，抛弃循环结构，能够进行全局并行计算；RNN 依赖上一时刻隐藏状态，难以并行。",
        "keywords": ["自注意力", "并行", "循环"],
    },
    {
        "filename": "二手房数据分析预测系统实验报告.docx",
        "question": "二手房数据分析预测系统主要解决了哪三类业务问题？",
        "reference": "主要解决信息不对称、市场反应滞后和交易效率低下三类问题。",
        "keywords": ["信息不对称", "市场", "效率"],
    },
    {
        "filename": "模式识别大作业报告.pdf",
        "question": "该模式识别报告的方法如何解决多尺度目标检测中的计算开销和尺度变化问题？",
        "reference": "通过尺度特定查询编码器进行端到端多尺度目标检测，避免固定尺度查询和分块带来的边界、内存与重复检测问题。",
        "keywords": ["尺度", "查询", "计算", "内存"],
    },
    {
        "filename": "人事管理流程.docx",
        "question": "员工办理入职通常需要提交哪些材料？",
        "reference": "通常需要身份证、银行卡、毕业证、职业资格证、原单位解除劳动关系证明，以及体检报告等材料。",
        "keywords": ["身份证", "银行卡", "毕业", "体检"],
    },
    {
        "filename": "软件工程复习.md",
        "question": "软件工程中四种常用过程模型分别是什么？",
        "reference": "瀑布模型、原型模型、增量模型和基于构件开发模型。",
        "keywords": ["瀑布", "原型", "增量", "构件"],
    },
    {
        "filename": "实验报告.docx",
        "question": "该数据可视化实验完成了哪些核心数据分析任务？",
        "reference": "完成网页数据获取、数据清洗与缺失值处理、结构化字段提取，以及多种数据可视化分析。",
        "keywords": ["获取", "清洗", "可视化", "Python"],
    },
    {
        "filename": "顺序表的插入，删除，查找，定位，合并实现.doc",
        "question": "顺序表执行插入操作时，为什么通常需要移动元素？",
        "reference": "顺序表使用连续存储，插入位置后的元素需要整体后移，为新元素腾出位置。",
        "keywords": ["移动", "后移", "插入"],
    },
    {
        "filename": "C语言课程设计报告.doc",
        "question": "该 C 语言课程设计报告主要包含了哪些课程设计内容？",
        "reference": "应包含课程设计题目、需求分析、数据结构或算法设计、功能实现、测试结果和总结。",
        "keywords": ["题目", "需求分析", "算法", "测试", "总结"],
    },
    {
        "filename": "LangChain常用API总结.pdf",
        "question": "LangChain 中 PromptTemplate 和 ChatPromptTemplate 的主要区别是什么？",
        "reference": "PromptTemplate 面向普通字符串提示词；ChatPromptTemplate 面向包含角色和不同类型消息的聊天提示词。",
        "keywords": ["字符串", "角色", "消息"],
    },
]

RESUME_EXPECTATIONS = {
    "【科研工程师】张三.pdf": "strong",
    "【NLP算法工程师】欧阳柳.pdf": "strong",
    "jianli-0012电子版简历免费模板1.docx": "weak",
    "jianli-0046蓝色好看的简历模板.docx": "weak",
    "ZWW-00060人力资源管理专业求职者简历模板.docx": "weak",
    "ZWW-00063软件工程学士JAVA工程师简历模板.docx": "strong",
    "ZWW-00073市场营销学士转企业法务简历模板.docx": "weak",
    "ZWW-00079市场营销专业实习生简历模板.docx": "weak",
}


def print_status(message: str) -> None:
    print(message, flush=True)


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((len(ordered) - 1) * ratio))
    return ordered[index]


def latency_summary(values: list[float]) -> dict[str, float]:
    return {
        "count": len(values),
        "avg_s": round(statistics.fmean(values), 3) if values else 0.0,
        "p50_s": round(percentile(values, 0.5), 3),
        "p95_s": round(percentile(values, 0.95), 3),
        "min_s": round(min(values), 3) if values else 0.0,
        "max_s": round(max(values), 3) if values else 0.0,
    }


def split_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    normalized = text.strip()
    if not normalized:
        return []
    chunks = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + chunk_size)
        chunks.append(normalized[start:end])
        if end >= len(normalized):
            break
        start = end - overlap
    return chunks


class ApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=None)
        self.token = ""

    async def close(self) -> None:
        await self.client.aclose()

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    async def login(self, username: str, password: str) -> None:
        response = await self.client.post(
            f"{self.base_url}/api/v1/auth/login",
            data={"username": username, "password": password},
        )
        response.raise_for_status()
        self.token = response.json()["access_token"]

    async def get_current_user(self) -> dict[str, Any]:
        response = await self.client.get(
            f"{self.base_url}/api/v1/auth/me", headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    async def create_knowledge_base(self, name: str) -> dict[str, Any]:
        response = await self.client.post(
            f"{self.base_url}/api/v1/knowledge-base/",
            headers=self.headers,
            json={
                "name": name,
                "description": "自动化验收测试知识库",
                "is_public": True,
                "is_searchable": True,
                "tags": ["acceptance-test"],
                "meta_data": {"created_by": "acceptance_test_kb_resume.py"},
            },
        )
        response.raise_for_status()
        return response.json()

    async def list_knowledge_bases(self) -> list[dict[str, Any]]:
        response = await self.client.get(
            f"{self.base_url}/api/v1/knowledge-base/",
            headers=self.headers,
            params={"skip": 0, "limit": 100},
        )
        response.raise_for_status()
        return response.json()

    async def create_conversation(self, title: str) -> dict[str, Any]:
        response = await self.client.post(
            f"{self.base_url}/api/v1/conversations/",
            headers=self.headers,
            json={"title": title, "description": "RAG acceptance test"},
        )
        response.raise_for_status()
        return response.json()

    async def upload_document(
        self, path: Path, knowledge_base_id: str
    ) -> dict[str, Any]:
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        with path.open("rb") as file_obj:
            response = await self.client.post(
                f"{self.base_url}/api/v1/documents/upload",
                headers=self.headers,
                data={
                    "knowledge_base_id": knowledge_base_id,
                    "category": "acceptance-test",
                },
                files={"file": (path.name, file_obj, mime_type)},
            )
        return {
            "status_code": response.status_code,
            "body": self._response_body(response),
        }

    async def process_document(self, document_id: str) -> dict[str, Any]:
        response = await self.client.post(
            f"{self.base_url}/api/v1/documents/{document_id}/process",
            headers=self.headers,
        )
        return {
            "status_code": response.status_code,
            "body": self._response_body(response),
        }

    async def get_document_chunks(self, document_id: str) -> dict[str, Any]:
        response = await self.client.get(
            f"{self.base_url}/api/v1/documents/{document_id}/chunks",
            headers=self.headers,
        )
        return {
            "status_code": response.status_code,
            "body": self._response_body(response),
        }

    async def get_knowledge_documents(
        self, knowledge_base_id: str
    ) -> list[dict[str, Any]]:
        response = await self.client.get(
            f"{self.base_url}/api/v1/knowledge-assistant/documents",
            headers=self.headers,
            params={
                "knowledge_base_id": knowledge_base_id,
                "skip": 0,
                "limit": 100,
            },
        )
        response.raise_for_status()
        return response.json().get("documents", [])

    async def ask(
        self,
        question: str,
        knowledge_base_id: str,
        conversation_id: str,
        context_limit: int,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        sources: list[dict[str, Any]] = []
        answer_parts: list[str] = []
        errors: list[str] = []
        async with self.client.stream(
            "POST",
            f"{self.base_url}/api/v1/knowledge-assistant/ask",
            headers=self.headers,
            data={
                "question": question,
                "knowledge_base_id": knowledge_base_id,
                "context_limit": str(context_limit),
                "conversation_history": "[]",
                "conversation_id": conversation_id,
            },
        ) as response:
            if response.status_code != 200:
                body = await response.aread()
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": body.decode("utf-8", errors="replace"),
                    "latency_s": round(time.perf_counter() - started, 3),
                }
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload = line[6:]
                if payload == "[DONE]":
                    break
                try:
                    event = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                event_type = event.get("type")
                if event_type == "start":
                    sources = event.get("sources") or []
                elif event_type == "chunk":
                    answer_parts.append(event.get("content") or "")
                elif event_type == "error":
                    errors.append(event.get("error") or "unknown error")
        return {
            "success": not errors,
            "status_code": 200,
            "answer": "".join(answer_parts),
            "sources": sources,
            "errors": errors,
            "latency_s": round(time.perf_counter() - started, 3),
        }

    async def list_job_descriptions(self) -> list[dict[str, Any]]:
        response = await self.client.get(
            f"{self.base_url}/api/v1/job-descriptions/",
            headers=self.headers,
            params={"page": 1, "size": 100},
        )
        response.raise_for_status()
        return response.json().get("items", [])

    async def create_job_description(self) -> dict[str, Any]:
        response = await self.client.post(
            f"{self.base_url}/api/v1/job-descriptions/save",
            headers=self.headers,
            json={
                "title": JD_TITLE,
                "department": "研发中心",
                "location": "不限",
                "salary_range": "面议",
                "experience_level": "1-5年",
                "education": "本科",
                "job_type": "全职",
                "skills": ["Java", "Python", "NLP", "机器学习", "Spring"],
                "content": (
                    "岗位职责：负责 Java 或 AI 软件系统设计、开发与优化；"
                    "参与数据处理、模型应用和工程化交付；与产品及算法团队协作。\n"
                    "任职要求：本科及以上；1-5 年软件研发经验；掌握 Java 或 Python；"
                    "具备 Spring、数据库、算法或 NLP 项目经验；具备良好沟通和工程能力。"
                ),
                "requirements": "本科，1-5 年经验，Java 或 AI/NLP 方向。",
                "status": "published",
                "workflow_type": "acceptance_test",
            },
        )
        return {
            "status_code": response.status_code,
            "body": self._response_body(response),
        }

    async def evaluate_resume(
        self, path: Path, job_description_id: str
    ) -> dict[str, Any]:
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        started = time.perf_counter()
        with path.open("rb") as file_obj:
            response = await self.client.post(
                f"{self.base_url}/api/v1/hr-workflows/evaluate",
                headers=self.headers,
                data={"job_description_id": job_description_id},
                files={"file": (path.name, file_obj, mime_type)},
            )
        return {
            "status_code": response.status_code,
            "latency_s": round(time.perf_counter() - started, 3),
            "body": self._response_body(response),
        }

    @staticmethod
    def _response_body(response: httpx.Response) -> Any:
        try:
            return response.json()
        except json.JSONDecodeError:
            return response.text


def judge_answer(answer: str, keywords: list[str]) -> dict[str, Any]:
    normalized = (answer or "").lower()
    matched = [keyword for keyword in keywords if keyword.lower() in normalized]
    hit_rate = len(matched) / len(keywords) if keywords else 0.0
    return {
        "correct": hit_rate >= 0.6,
        "score": int(hit_rate >= 0.6),
        "hit_rate": round(hit_rate, 4),
        "matched_keywords": matched,
        "missing_keywords": [keyword for keyword in keywords if keyword not in matched],
    }


async def ingest_documents(
    api: ApiClient, knowledge_base_id: str, user_id: str
) -> list[dict[str, Any]]:
    results = []
    embeddings = get_embedding_service().get_embeddings()
    collection_name = f"document_chunks_{user_id}".replace("-", "_")
    vector_store = PGVector(
        connection=settings.DATABASE_URL,
        embeddings=embeddings,
        collection_name=collection_name,
        use_jsonb=True,
    )
    await asyncio.to_thread(vector_store.create_tables_if_not_exists)

    files = sorted(path for path in KNOWLEDGE_DIR.iterdir() if path.is_file())
    for index, path in enumerate(files, start=1):
        print_status(f"[KB {index}/{len(files)}] 上传 {path.name}")
        upload = await api.upload_document(path, knowledge_base_id)
        document = upload["body"] if isinstance(upload["body"], dict) else {}
        document_id = document.get("id")
        parse_error = None
        ingest_error = None
        extracted_content = ""
        chunk_count = 0
        parse_latency = 0.0
        if upload["status_code"] == 200 and document_id:
            print_status(f"[KB {index}/{len(files)}] 解析并向量化 {path.name}")
            parse_started = time.perf_counter()
            try:
                mime_type = mimetypes.guess_type(path.name)[0] or ""
                extracted_content = await extract_text_content(str(path), mime_type)
                parse_latency = time.perf_counter() - parse_started
                chunks = split_text(extracted_content)
                chunk_count = len(chunks)
                if extracted_content.strip() and chunks:
                    langchain_docs = [
                        LangChainDocument(
                            page_content=chunk_text,
                            metadata={
                                "document_id": document_id,
                                "knowledge_base_id": knowledge_base_id,
                                "chunk_index": chunk_index,
                                "chunk_size": len(chunk_text),
                                "filename": path.name,
                                "category": "acceptance-test",
                                "source_type": "content",
                                "collection_name": collection_name,
                            },
                        )
                        for chunk_index, chunk_text in enumerate(chunks)
                    ]
                    await asyncio.to_thread(
                        vector_store.add_documents, langchain_docs
                    )
                    async with AsyncSessionLocal() as session:
                        await session.execute(
                            update(Document)
                            .where(Document.id == document_id)
                            .values(extracted_content=extracted_content)
                        )
                        await session.commit()
            except Exception as exc:
                if not extracted_content.strip():
                    parse_error = f"{type(exc).__name__}: {exc}"
                else:
                    ingest_error = f"{type(exc).__name__}: {exc}"

        parse_success = bool(extracted_content.strip())
        ingest_success = bool(parse_success and chunk_count and not ingest_error)
        results.append(
            {
                "filename": path.name,
                "document_id": document_id,
                "upload_status": upload["status_code"],
                "parse_success": parse_success,
                "ingest_success": ingest_success,
                "parse_latency_s": round(parse_latency, 3),
                "extracted_chars": len(extracted_content),
                "chunk_count": chunk_count,
                "upload_error": None
                if upload["status_code"] == 200
                else upload["body"],
                "parse_error": parse_error,
                "ingest_error": ingest_error,
            }
        )
    return results


async def load_existing_ingestion(
    api: ApiClient, knowledge_base_id: str
) -> list[dict[str, Any]]:
    documents = await api.get_knowledge_documents(knowledge_base_id)
    results = []
    for document in documents:
        document_id = document["id"]
        chunks = await api.get_document_chunks(document_id)
        chunk_rows = (
            chunks["body"].get("chunks", [])
            if chunks["status_code"] == 200
            and isinstance(chunks["body"], dict)
            else []
        )
        extracted_content = document.get("extracted_content") or ""
        results.append(
            {
                "filename": document.get("original_filename")
                or document.get("filename"),
                "document_id": document_id,
                "upload_status": 200,
                "parse_success": bool(extracted_content.strip()),
                "ingest_success": bool(extracted_content.strip() and chunk_rows),
                "parse_latency_s": 0.0,
                "extracted_chars": len(extracted_content),
                "chunk_count": len(chunk_rows),
                "upload_error": None,
                "parse_error": None,
                "ingest_error": None
                if chunk_rows
                else f"chunk query status {chunks['status_code']}",
            }
        )
    return results


def source_titles(sources: list[dict[str, Any]]) -> list[str]:
    titles = []
    for source in sources:
        title = source.get("document_title") or source.get("filename")
        if title and title not in titles:
            titles.append(title)
    return titles


def score_doc(source: dict[str, Any]) -> float:
    return float(
        source.get("original_score")
        or source.get("combined_score")
        or source.get("content_score")
        or 0.0
    )


def has_real_rerank_scores(sources: list[dict[str, Any]]) -> bool:
    scores = [
        float(source["rerank_score"])
        for source in sources
        if "rerank_score" in source
    ]
    if len(scores) < 3:
        return False
    fallback = [1.0 - index * 0.1 for index in range(len(scores))]
    return not all(
        abs(actual - expected) < 1e-6
        for actual, expected in zip(scores, fallback)
    )


async def evaluate_rag(
    api: ApiClient,
    knowledge_base_id: str,
    conversation_id: str,
    ingestion: list[dict[str, Any]],
) -> dict[str, Any]:
    ingested_titles = {
        item["filename"] for item in ingestion if item["ingest_success"]
    }
    details = []
    for index, label in enumerate(KNOWLEDGE_QUESTIONS, start=1):
        print_status(f"[RAG {index}/{len(KNOWLEDGE_QUESTIONS)}] {label['question']}")
        result = await api.ask(
            question=label["question"],
            knowledge_base_id=knowledge_base_id,
            conversation_id=conversation_id,
            context_limit=10,
        )
        sources = result.get("sources") or []
        returned_titles = source_titles(sources)
        rerank_available = has_real_rerank_scores(sources)
        pre_rerank = sorted(sources, key=score_doc, reverse=True)
        pre_titles = source_titles(pre_rerank)
        expected = label["filename"]
        answer = result.get("answer") or ""
        judge = judge_answer(answer, label["keywords"])
        details.append(
            {
                **label,
                "expected_document_ingested": expected in ingested_titles,
                "success": result.get("success"),
                "latency_s": result.get("latency_s"),
                "answer": answer,
                "answer_correct": judge["correct"],
                "answer_judgement": judge,
                "returned_top5": returned_titles[:5],
                "recall_at_5": expected in returned_titles[:5],
                "pre_rerank_top5": pre_titles[:5],
                "pre_rerank_recall_at_5": expected in pre_titles[:5],
                "citation_correct_top1": bool(
                    returned_titles and returned_titles[0] == expected
                ),
                "rerank_available": rerank_available,
                "errors": result.get("errors") or [],
            }
        )

    total = len(details)
    rerank_samples = [item for item in details if item["rerank_available"]]
    return {
        "question_count": total,
        "answer_accuracy": round(
            sum(item["answer_correct"] for item in details) / total, 4
        ),
        "citation_accuracy_top1": round(
            sum(item["citation_correct_top1"] for item in details) / total, 4
        ),
        "recall_at_5": round(sum(item["recall_at_5"] for item in details) / total, 4),
        "pre_rerank_recall_at_5": round(
            sum(item["pre_rerank_recall_at_5"] for item in details) / total, 4
        ),
        "rerank_available": bool(rerank_samples),
        "rerank_sample_count": len(rerank_samples),
        "rerank_recall_at_5": (
            round(
                sum(item["recall_at_5"] for item in rerank_samples)
                / len(rerank_samples),
                4,
            )
            if rerank_samples
            else None
        ),
        "latency": latency_summary(
            [float(item["latency_s"] or 0.0) for item in details]
        ),
        "details": details,
    }


async def ensure_job_description(api: ApiClient) -> dict[str, Any]:
    existing = await api.list_job_descriptions()
    for item in existing:
        if item.get("title") == JD_TITLE:
            return item
    created = await api.create_job_description()
    if created["status_code"] != 200:
        raise RuntimeError(f"create JD failed: {created['body']}")
    return created["body"]


async def evaluate_resumes(api: ApiClient) -> dict[str, Any]:
    job_description = await ensure_job_description(api)
    job_description_id = job_description["id"]
    files = sorted(path for path in RESUME_DIR.iterdir() if path.is_file())
    details = []
    for index, path in enumerate(files, start=1):
        print_status(f"[RESUME {index}/{len(files)}] 评分 {path.name}")
        result = await api.evaluate_resume(path, job_description_id)
        body = result["body"] if isinstance(result["body"], dict) else {}
        score = body.get("total_score")
        expected = RESUME_EXPECTATIONS.get(path.name, "unknown")
        predicted_qualified = (
            float(score) >= 60
            if result["status_code"] == 200 and score is not None
            else None
        )
        details.append(
            {
                "filename": path.name,
                "expected": expected,
                "status_code": result["status_code"],
                "latency_s": result["latency_s"],
                "candidate_name": body.get("name"),
                "position": body.get("position"),
                "total_score": score,
                "predicted_qualified": predicted_qualified,
                "error": None if result["status_code"] == 200 else result["body"],
            }
        )

    valid = [
        item
        for item in details
        if item["status_code"] == 200 and item["total_score"] is not None
    ]
    strong = [
        float(item["total_score"]) for item in valid if item["expected"] == "strong"
    ]
    weak = [
        float(item["total_score"]) for item in valid if item["expected"] == "weak"
    ]
    pair_count = len(strong) * len(weak)
    correct_pairs = sum(
        strong_score > weak_score
        for strong_score in strong
        for weak_score in weak
    )
    classification_correct = sum(
        (item["expected"] == "strong" and item["predicted_qualified"])
        or (item["expected"] == "weak" and not item["predicted_qualified"])
        for item in valid
    )
    return {
        "job_description": {
            "id": job_description_id,
            "title": job_description.get("title"),
        },
        "resume_count": len(files),
        "success_count": len(valid),
        "classification_accuracy_at_60": (
            round(classification_correct / len(valid), 4) if valid else None
        ),
        "pairwise_ranking_accuracy": (
            round(correct_pairs / pair_count, 4) if pair_count else None
        ),
        "strong_avg_score": round(statistics.fmean(strong), 2) if strong else None,
        "weak_avg_score": round(statistics.fmean(weak), 2) if weak else None,
        "latency": latency_summary(
            [float(item["latency_s"]) for item in details]
        ),
        "details": details,
    }


async def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["kb", "resume", "all"], default="all")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--username", default="testuser")
    parser.add_argument("--password", default="test123")
    parser.add_argument("--kb-name", default="验收测试-KB-20260910")
    parser.add_argument("--kb-id")
    parser.add_argument("--skip-ingest", action="store_true")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    api = ApiClient(args.base_url)
    try:
        await api.login(args.username, args.password)
        current_user = await api.get_current_user()
        print_status(f"登录成功: {current_user.get('username')}")
        output_path = Path(args.output)
        if args.stage == "resume" and output_path.exists():
            result = json.loads(output_path.read_text(encoding="utf-8"))
        else:
            result: dict[str, Any] = {
                "test_date": "2026-09-10",
                "base_url": args.base_url,
                "user": current_user.get("username"),
            }

        if args.stage in {"kb", "all"}:
            if args.kb_id:
                knowledge_base_id = args.kb_id
            else:
                knowledge_bases = await api.list_knowledge_bases()
                knowledge_base = next(
                    (
                        item
                        for item in knowledge_bases
                        if item.get("name") == args.kb_name
                    ),
                    None,
                )
                if not knowledge_base:
                    knowledge_base = await api.create_knowledge_base(args.kb_name)
                knowledge_base_id = knowledge_base["id"]
            print_status(f"知识库: {args.kb_name} ({knowledge_base_id})")
            if args.skip_ingest:
                ingestion = await load_existing_ingestion(
                    api, knowledge_base_id
                )
            else:
                ingestion = await ingest_documents(
                    api, knowledge_base_id, str(current_user["id"])
                )
            conversation = await api.create_conversation("RAG 验收测试")
            rag = await evaluate_rag(
                api,
                knowledge_base_id,
                conversation["id"],
                ingestion,
            )
            result["knowledge_base"] = {
                "id": knowledge_base_id,
                "name": args.kb_name,
                "document_count": len(ingestion),
                "parse_success_count": sum(
                    item["parse_success"] for item in ingestion
                ),
                "parse_success_rate": round(
                    sum(item["parse_success"] for item in ingestion)
                    / len(ingestion),
                    4,
                ),
                "ingest_success_count": sum(
                    item["ingest_success"] for item in ingestion
                ),
                "ingest_success_rate": round(
                    sum(item["ingest_success"] for item in ingestion)
                    / len(ingestion),
                    4,
                ),
                "ingestion": ingestion,
                "rag": rag,
            }
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print_status(f"知识库阶段结果已写入: {output_path}")

        if args.stage in {"resume", "all"}:
            result["resume_evaluation"] = await evaluate_resumes(api)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print_status(f"结果已写入: {output_path}")
    finally:
        await api.close()


if __name__ == "__main__":
    asyncio.run(main())
