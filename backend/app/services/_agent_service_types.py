

from dataclasses import dataclass
from typing import List, Optional

"""
    共享数据类
"""

@dataclass(frozen=True)
class AgentToolSpec:
    """
    Agent 可规划调用的工具声明

    字段:
        name：工具名称，例如 generate_jd。
        intent：意图标签，例如 jd、resume_screening。
        route：前端应该跳转或关联的页面路由。
        description：工具能力说明。
        prerequisites：执行前置条件。
    """

    name: str
    intent: str
    route: Optional[str]
    description: str
    prerequisites: List[str]

@dataclass(frozen=True)
class ReActDecision:
    """
    ReAct 单轮决策结果:表示一次 Agent 决策结果
        这里的 ReAct 不是开放式工具调用，而是“受控 ReAct”：模型只能在固定动作空间里选，不能随意执行代码或调用未知工具。

    字段说明：
        mode：chat 或 tool。
        intent：识别出的业务意图。
        action：chat、use_tool、ask_user。
        thought：给产品侧展示的简短推理摘要。不承载模型的完整隐藏推理过程
        observation：当前观察或预期结果。
        confidence：置信度。
        reply：普通聊天时的自然语言回复。
        source：来源，例如 react_llm 或 fallback。
    """

    mode: str
    intent: str
    action: str
    thought: str
    observation: str
    confidence: Optional[float] = None
    reply: Optional[str] = None
    source: str = "react"
