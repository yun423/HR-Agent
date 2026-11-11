"""Reproducible component benchmark for HR Agent.

This script is intentionally read-only against business data. It measures:
1. Remote service read latency.
2. LLM JD generation latency and structure compliance.
3. Embedding retrieval recall on a synthetic FAQ corpus.
4. Optional Qwen rerank improvement.
5. Dify-equivalent resume scoring behavior at the model layer.
6. A component-level RAG latency estimate without PostgreSQL/pgvector.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
import statistics
import time
from typing import Any
from uuid import UUID

import httpx

from app.core.config import settings
from app.services.embedding_service import get_embedding_service
from app.services.llm_service import LLMService


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, math.ceil(len(ordered) * ratio) - 1)
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


def cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object found")
    return json.loads(cleaned[start : end + 1])


async def measure_remote_reads(user_id: UUID, iterations: int) -> dict[str, Any]:
    url = (
        f"http://{settings.HR_SERVICE_HOST}:{settings.HR_SERVICE_PORT}"
        f"/api/v1/job-descriptions/"
    )
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": settings.HR_SERVICE_APIKEY,
    }
    params = {
        "current_user_id": str(user_id),
        "page": 1,
        "size": 100,
    }

    values: list[float] = []
    statuses: list[int] = []
    returned_counts: list[int] = []
    for _ in range(iterations):
        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)
        values.append(time.perf_counter() - started)
        statuses.append(response.status_code)
        if response.status_code == 200:
            payload = response.json()
            returned_counts.append(len(payload.get("items", [])))

    return {
        "endpoint": "/api/v1/job-descriptions/",
        "page_size": 100,
        "success_rate": round(
            sum(status == 200 for status in statuses) / len(statuses), 4
        ),
        "returned_counts": returned_counts,
        "latency": latency_summary(values),
    }


JD_CASES = [
    "招聘高级 Java 后端工程师，北京，5 年经验，本科，负责微服务、MySQL、Redis。",
    "招聘 AI 产品经理，上海，3 年经验，本科，负责任务规划、指标设计和跨团队交付。",
    "招聘前端工程师，深圳，3-5 年经验，本科，负责 Vue3、性能优化和组件体系。",
    "招聘财务经理，杭州，5 年以上经验，本科，负责预算、报表和经营分析。",
    "招聘测试开发工程师，成都，3 年经验，本科，负责自动化测试平台和质量体系。",
]


async def generate_one_jd(llm: LLMService, prompt: str) -> dict[str, Any]:
    started = time.perf_counter()
    response = await llm.client.chat.completions.create(
        model=llm.llm_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "你是资深招聘专家。请输出完整中文 JD，必须包含岗位职责、"
                    "任职要求、优先条件三个部分，并使用 Markdown 标题。"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=1200,
    )
    content = response.choices[0].message.content or ""
    required_sections = ["岗位职责", "任职要求", "优先条件"]
    return {
        "latency_s": round(time.perf_counter() - started, 3),
        "content_chars": len(content),
        "section_compliance": all(section in content for section in required_sections),
    }


async def measure_jd_generation(llm: LLMService) -> dict[str, Any]:
    sequential = []
    for prompt in JD_CASES:
        sequential.append(await generate_one_jd(llm, prompt))

    concurrent_started = time.perf_counter()
    concurrent = await asyncio.gather(
        *(generate_one_jd(llm, prompt) for prompt in JD_CASES)
    )
    concurrent_wall_s = time.perf_counter() - concurrent_started

    latencies = [item["latency_s"] for item in sequential + concurrent]
    return {
        "cases_per_batch": len(JD_CASES),
        "sequential_success_rate": round(
            sum(item["section_compliance"] for item in sequential) / len(sequential),
            4,
        ),
        "concurrency_5_success_rate": round(
            sum(item["section_compliance"] for item in concurrent) / len(concurrent),
            4,
        ),
        "concurrency_5_wall_s": round(concurrent_wall_s, 3),
        "concurrency_5_throughput_jobs_per_s": round(
            len(concurrent) / concurrent_wall_s, 3
        ),
        "latency": latency_summary(latencies),
    }


FAQ_TOPICS = [
    (
        "annual_leave",
        "年假",
        [
            "工作满一年可享每年 5 天带薪年假，按自然年折算。",
            "第二年起每年新增 1 天，年假额度在 1 月 1 日刷新。",
            "年假申请需至少提前两个工作日提交。",
            "未休年假经主管确认后可结转至次年三月。",
            "试用期员工按在岗月份折算年假。",
            "离职时未休年假按日工资折算结算。",
            "连续病假超过一个月会影响当年年假折算。",
            "法定节假日不计入年假天数。",
            "年假审批人依次为直属主管和部门负责人。",
            "年假余额可在员工自助系统实时查询。",
        ],
    ),
    (
        "sick_leave",
        "病假",
        [
            "病假超过一天需提交医疗机构证明。",
            "病假申请由员工在返岗后两个工作日内补录。",
            "连续病假三天以内由直属主管审批。",
            "连续病假超过三天需部门负责人复核。",
            "长期病假应同步联系 HR 确认医疗期。",
            "病假期间工资按当地政策执行。",
            "急诊可先口头报备，事后补交材料。",
            "病假证明需包含就诊日期和休息建议。",
            "员工不得用年假替代未提交证明的病假。",
            "病假记录仅向权限内人员展示。",
        ],
    ),
    (
        "expense",
        "报销",
        [
            "差旅报销应在行程结束后十五天内提交。",
            "单笔超过 5000 元的报销需财务负责人审批。",
            "交通票据必须与出差申请单关联。",
            "电子发票需上传原始 PDF 文件。",
            "餐饮报销需注明参与人员和业务目的。",
            "跨月发票最迟在下月十日前提交。",
            "固定资产采购不适用普通费用报销流程。",
            "报销款通常在审批完成后五个工作日到账。",
            "遗失票据需填写费用说明并提供支付记录。",
            "预算超支项目需先获得预算负责人批准。",
        ],
    ),
    (
        "onboarding",
        "入职",
        [
            "入职当天需提交身份证、学历证明和银行卡信息。",
            "背调通过后才会发放正式录用通知。",
            "新员工账号在入职前一个工作日创建。",
            "入职培训在首个自然月内完成。",
            "试用期目标由直属主管在入职一周内确认。",
            "劳动合同通过电子签平台完成签署。",
            "办公设备由 IT 在入职日交付。",
            "应届生入职需补充三方协议归档。",
            "外籍员工入职需核验工作许可。",
            "离职未满六个月的回聘人员需额外审批。",
        ],
    ),
    (
        "social_security",
        "社保公积金",
        [
            "社保基数每年七月按政策统一调整。",
            "新员工当月十五日前入职可当月参保。",
            "公积金比例变更需提交书面申请。",
            "跨城市转移社保需提供原参保地凭证。",
            "补充医疗保险在转正后生效。",
            "社保缴纳城市与实际办公城市不一致时需审批。",
            "员工可在自助系统下载缴费证明。",
            "公积金贷款证明由 HR 每周集中办理。",
            "缴费异常通常在三个工作日内修正。",
            "离职当月社保按当地截止日规则处理。",
        ],
    ),
    (
        "performance",
        "绩效",
        [
            "绩效申诉应在结果公布后五个工作日内提出。",
            "季度目标调整需要直属主管和 HRBP 共同确认。",
            "绩效校准会由部门负责人组织。",
            "强制分布不适用于少于十人的团队。",
            "绩效结果与年度调薪在独立流程中处理。",
            "低绩效改进计划周期通常为六十天。",
            "员工可在系统查看历史和当前绩效目标。",
            "跨部门项目的评价需收集协作方反馈。",
            "晋升评审每年开展两次。",
            "绩效材料保存期限为三年。",
        ],
    ),
    (
        "transfer",
        "调岗",
        [
            "内部调岗需当前主管和目标主管双方同意。",
            "调岗面试通过后由 HR 发起异动流程。",
            "跨城市调岗包含搬迁支持政策。",
            "试用期内调岗需额外说明业务原因。",
            "调岗生效日通常为每月一日或十六日。",
            "岗位级别变化需同步完成职级评审。",
            "调岗后的试用期由新岗位政策决定。",
            "涉及薪酬变化的调岗需薪酬团队审批。",
            "员工拒绝调岗时应由 HR 协调沟通。",
            "调岗记录会同步更新组织通讯录。",
        ],
    ),
    (
        "remote_work",
        "远程办公",
        [
            "远程办公每周最多申请两天。",
            "远程办公需保证核心时段在线。",
            "敏感数据不得在公共网络环境处理。",
            "居家办公设备由员工自行保障网络。",
            "跨时区协作可申请临时弹性时段。",
            "远程办公申请由直属主管审批。",
            "连续远程办公超过一周需部门负责人批准。",
            "远程会议应开启字幕或记录关键结论。",
            "客户现场办公按差旅制度处理。",
            "远程办公不改变劳动合同履行地。",
        ],
    ),
    (
        "training",
        "培训",
        [
            "外部培训费用超过 3000 元需签署服务期协议。",
            "培训申请应说明课程目标和工作关联。",
            "年度培训预算由部门在十二月申报。",
            "认证考试通过后可报销首次考试费。",
            "培训缺席需提前二十四小时取消。",
            "内部讲师课酬按课程时长计算。",
            "学习平台课程完成记录自动同步。",
            "关键岗位培训需指定替补人员。",
            "海外培训需完成合规和签证审核。",
            "培训服务期通常为十二个月。",
        ],
    ),
    (
        "offboarding",
        "离职",
        [
            "主动离职需提前三十天提交书面通知。",
            "离职交接清单由直属主管确认。",
            "最后工作日当天归还门禁卡和电脑。",
            "离职证明在手续完成后三个工作日出具。",
            "竞业限制补偿按协议约定执行。",
            "离职前需完成费用报销和借款清理。",
            "权限将在最后工作日十八点统一回收。",
            "离职访谈由 HRBP 安排。",
            "未使用的福利积分在离职日失效。",
            "离职后仍需履行保密义务。",
        ],
    ),
]


def build_faq_corpus() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    documents: list[dict[str, str]] = []
    for topic, label, entries in FAQ_TOPICS:
        for index, text in enumerate(entries):
            documents.append(
                {
                    "id": f"{topic}-{index}",
                    "category": label,
                    "text": f"{label} FAQ，场景编号 {topic}-{index}：{text}",
                }
            )

    queries = [
        {"query": "工作满一年有多少天带薪年假？", "target": "annual_leave-0"},
        {"query": "年假额度什么时候刷新？", "target": "annual_leave-1"},
        {"query": "病假超过一天需要什么材料？", "target": "sick_leave-0"},
        {"query": "连续病假三天由谁审批？", "target": "sick_leave-2"},
        {"query": "差旅报销的提交期限是多久？", "target": "expense-0"},
        {"query": "大额报销需要谁审批？", "target": "expense-1"},
        {"query": "入职当天要带哪些证件？", "target": "onboarding-0"},
        {"query": "背调什么时候完成？", "target": "onboarding-1"},
        {"query": "社保基数什么时候调整？", "target": "social_security-0"},
        {"query": "新员工什么时候可以参保？", "target": "social_security-1"},
        {"query": "绩效申诉的时限是多久？", "target": "performance-0"},
        {"query": "低绩效改进计划持续多久？", "target": "performance-5"},
        {"query": "内部调岗需要谁同意？", "target": "transfer-0"},
        {"query": "调岗生效日一般是什么时候？", "target": "transfer-4"},
        {"query": "每周可以远程办公几天？", "target": "remote_work-0"},
        {"query": "连续远程办公一周以上怎么审批？", "target": "remote_work-6"},
        {"query": "外部培训超过多少钱要签服务期？", "target": "training-0"},
        {"query": "认证考试费用可以报销吗？", "target": "training-3"},
        {"query": "主动离职需要提前多久通知？", "target": "offboarding-0"},
        {"query": "离职证明多久能拿到？", "target": "offboarding-3"},
    ]
    return documents, queries


def rank_documents(
    query_vector: list[float],
    documents: list[dict[str, str]],
    document_vectors: list[list[float]],
) -> list[str]:
    ranked = sorted(
        (
            (cosine_similarity(query_vector, vector), document["id"])
            for document, vector in zip(documents, document_vectors)
        ),
        key=lambda item: item[0],
        reverse=True,
    )
    return [document_id for _, document_id in ranked]


def retrieval_metrics(
    documents: list[dict[str, str]],
    queries: list[dict[str, str]],
    rankings: list[list[str]],
) -> dict[str, Any]:
    reciprocal_ranks = []
    recall_at_1 = 0
    recall_at_5 = 0
    for query, ranking in zip(queries, rankings):
        target = query["target"]
        rank = ranking.index(target) + 1
        reciprocal_ranks.append(1 / rank)
        recall_at_1 += int(rank <= 1)
        recall_at_5 += int(rank <= 5)

    return {
        "document_count": len(documents),
        "query_count": len(queries),
        "recall_at_1": round(recall_at_1 / len(queries), 4),
        "recall_at_5": round(recall_at_5 / len(queries), 4),
        "mrr": round(statistics.fmean(reciprocal_ranks), 4),
    }


async def measure_retrieval() -> dict[str, Any]:
    documents, queries = build_faq_corpus()
    embeddings = get_embedding_service().get_embeddings()

    started = time.perf_counter()
    document_vectors = await asyncio.to_thread(
        embeddings.embed_documents, [item["text"] for item in documents]
    )
    document_embedding_s = time.perf_counter() - started

    query_latencies = []
    query_vectors = []
    for item in queries:
        started = time.perf_counter()
        query_vectors.append(await asyncio.to_thread(embeddings.embed_query, item["query"]))
        query_latencies.append(time.perf_counter() - started)

    rankings = [
        rank_documents(query_vector, documents, document_vectors)
        for query_vector in query_vectors
    ]
    base_metrics = retrieval_metrics(documents, queries, rankings)

    rerank_metrics = None
    rerank_latency = None
    rerank_error = None
    try:
        import dashscope
        from dashscope import TextReRank

        dashscope.api_key = settings.QWEN_API_KEY

        def rerank_one(query: str, candidates: list[str]) -> list[str]:
            response = TextReRank.call(
                model=settings.QWEN_MODEL,
                query=query,
                documents=candidates,
                top_n=len(candidates),
                return_documents=False,
            )
            if response.status_code != 200:
                raise RuntimeError(
                    f"{response.status_code}: {getattr(response, 'message', '')}"
                )
            ordered = sorted(
                response.output.results,
                key=lambda item: item.relevance_score,
                reverse=True,
            )
            return [candidates[item.index] for item in ordered]

        document_by_id = {item["id"]: item["text"] for item in documents}
        reranked_rankings = []
        rerank_times = []
        for query, ranking in zip(queries, rankings):
            candidates = [document_by_id[document_id] for document_id in ranking[:10]]
            started = time.perf_counter()
            reranked_texts = await asyncio.to_thread(rerank_one, query["query"], candidates)
            rerank_times.append(time.perf_counter() - started)
            text_to_id = {text: document_id for document_id, text in document_by_id.items()}
            rerank_rankings.append(
                [text_to_id[text] for text in reranked_texts]
                + ranking[10:]
            )
        rerank_metrics = retrieval_metrics(documents, queries, rerank_rankings)
        rerank_latency = latency_summary(rerank_times)
    except Exception as exc:
        rerank_error = f"{type(exc).__name__}: {exc}"

    return {
        "document_embedding_wall_s": round(document_embedding_s, 3),
        "query_embedding_latency": latency_summary(query_latencies),
        "embedding_only": base_metrics,
        "qwen_rerank_top10_to_top5": rerank_metrics,
        "qwen_rerank_latency": rerank_latency,
        "rerank_error": rerank_error,
    }


RESUME_CASES = [
    {
        "name": "A",
        "expected": "strong",
        "text": (
            "5 年 Java 后端经验，本科，主导 Spring Cloud 微服务、MySQL 调优、"
            "Redis 缓存和高并发订单系统，带过 4 人小组。"
        ),
    },
    {
        "name": "B",
        "expected": "strong",
        "text": (
            "4 年 Java 服务端经验，本科，负责交易系统、Spring Boot、PostgreSQL、"
            "Kafka 和容器化部署，有性能优化项目。"
        ),
    },
    {
        "name": "C",
        "expected": "strong",
        "text": (
            "3 年 Java 开发经验，本科，熟悉 Spring、MySQL、Redis，参与支付网关"
            "与监控告警平台开发，能独立负责模块。"
        ),
    },
    {
        "name": "D",
        "expected": "weak",
        "text": "3 年 Vue 前端经验，本科，熟悉组件库、页面性能优化和 Node 构建。",
    },
    {
        "name": "E",
        "expected": "weak",
        "text": "应届本科，仅有 6 个月 Java 课程项目和实习经历，没有生产系统经验。",
    },
    {
        "name": "F",
        "expected": "weak",
        "text": "6 年销售经验，本科，负责渠道拓展和客户关系，无编程工作经历。",
    },
]


async def score_resume(llm: LLMService, candidate: dict[str, str]) -> dict[str, Any]:
    prompt = f"""
岗位：Java 后端工程师
要求：本科，3-5 年经验，熟练掌握 Java、Spring、MySQL、Redis，有微服务经验。
简历：{candidate['text']}

请严格返回 JSON：
{{"total_score": 0-100 的整数, "fit_level": "strong|medium|weak",
  "reason": "一句话理由"}}
"""
    started = time.perf_counter()
    response = await llm.client.chat.completions.create(
        model=llm.llm_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=300,
    )
    content = response.choices[0].message.content or ""
    parsed = extract_json_object(content)
    return {
        "name": candidate["name"],
        "expected": candidate["expected"],
        "score": int(parsed["total_score"]),
        "fit_level": parsed.get("fit_level"),
        "latency_s": round(time.perf_counter() - started, 3),
        "valid_json": True,
    }


async def measure_resume_scoring(llm: LLMService) -> dict[str, Any]:
    results = []
    failures = []
    for candidate in RESUME_CASES:
        try:
            results.append(await score_resume(llm, candidate))
        except Exception as exc:
            failures.append(
                {
                    "name": candidate["name"],
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    strong = [item["score"] for item in results if item["expected"] == "strong"]
    weak = [item["score"] for item in results if item["expected"] == "weak"]
    pair_count = len(strong) * len(weak)
    correct_pairs = sum(strong_score > weak_score for strong_score in strong for weak_score in weak)

    return {
        "case_count": len(RESUME_CASES),
        "valid_json_count": len(results),
        "failure_count": len(failures),
        "failures": failures,
        "scores": results,
        "strong_avg_score": round(statistics.fmean(strong), 2) if strong else None,
        "weak_avg_score": round(statistics.fmean(weak), 2) if weak else None,
        "pairwise_ranking_accuracy": (
            round(correct_pairs / pair_count, 4) if pair_count else None
        ),
        "latency": latency_summary([item["latency_s"] for item in results]),
    }


async def measure_component_rag(llm: LLMService) -> dict[str, Any]:
    documents, queries = build_faq_corpus()
    embeddings = get_embedding_service().get_embeddings()
    document_vectors = await asyncio.to_thread(
        embeddings.embed_documents, [item["text"] for item in documents]
    )
    document_by_id = {item["id"]: item for item in documents}

    stages: list[dict[str, float]] = []
    for item in queries[:3]:
        started = time.perf_counter()
        query_vector = await asyncio.to_thread(embeddings.embed_query, item["query"])
        embedding_s = time.perf_counter() - started

        started = time.perf_counter()
        ranking = rank_documents(query_vector, documents, document_vectors)
        context = "\n".join(document_by_id[document_id]["text"] for document_id in ranking[:5])
        retrieval_s = time.perf_counter() - started

        started = time.perf_counter()
        response = await llm.client.chat.completions.create(
            model=llm.llm_model,
            messages=[
                {
                    "role": "system",
                    "content": "仅根据给定上下文回答，答案需简洁准确。",
                },
                {"role": "user", "content": f"问题：{item['query']}\n上下文：{context}"},
            ],
            temperature=0,
            max_tokens=300,
        )
        generation_s = time.perf_counter() - started
        stages.append(
            {
                "embedding_s": round(embedding_s, 3),
                "retrieval_s": round(retrieval_s, 3),
                "generation_s": round(generation_s, 3),
                "total_s": round(embedding_s + retrieval_s + generation_s, 3),
                "answer_chars": len(response.choices[0].message.content or ""),
            }
        )

    return {
        "case_count": len(stages),
        "note": "Component concatenation only; excludes HTTP, pgvector, rerank and streaming overhead.",
        "stages": stages,
        "total_latency": latency_summary([item["total_s"] for item in stages]),
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--user-id",
        default="388ec33b-6b01-45cb-ba07-c2f7d11dd026",
        help="Existing remote-service user id used for read-only list requests.",
    )
    parser.add_argument("--remote-iterations", type=int, default=10)
    args = parser.parse_args()

    llm = LLMService()
    result = {
        "config": {
            "llm_model": settings.LLM_MODEL,
            "embedding_model": settings.EMBEDDING_MODEL,
            "vector_dimension": settings.VECTOR_DIMENSION,
            "context_limit": settings.CONTEXT_LIMIT,
            "rerank_enabled": settings.RERANK_ENABLED,
            "rerank_top_k": settings.RERANK_TOP_K,
            "rerank_final_k": settings.RERANK_FINAL_K,
            "rerank_model": settings.QWEN_MODEL,
        },
        "remote_read": await measure_remote_reads(
            UUID(args.user_id), args.remote_iterations
        ),
        "jd_generation": await measure_jd_generation(llm),
        "retrieval": await measure_retrieval(),
        "resume_scoring": await measure_resume_scoring(llm),
        "component_rag": await measure_component_rag(llm),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
