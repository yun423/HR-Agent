"""
    Agent的技能分发器。读取本地 skill目录里的SKILL.md 和 manifest信息，把一个技能拆成不同phase，
        例如草稿、确认、执行等，再通过 AgentSkillDispatcher 按 intent 和 phase 分发。
        ScriptedSkillPhase 可以加载并执行技能脚本，因此这个文件是 Agent 和可插拔技能之间的桥。
"""
from __future__ import annotations

import importlib.util
import inspect
import logging
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SkillMetadata:
    name: str
    description: str
    intent: str
    route: Optional[str]
    prerequisites: tuple[str, ...]
    phases: tuple[str, ...]
    default_phase: str
    confirmation_action: Optional[str] = None


@dataclass(frozen=True)
class SkillPhaseDefinition:
    phase_name: str
    script_path: Path
    function_name: str


class ScriptedSkillPhase:
    """技能阶段由技能包中的Python脚本执行."""

    def __init__(self, skill_dir: Path, definition: SkillPhaseDefinition):
        self.skill_dir = skill_dir
        self.definition = definition

    @property
    def skill_markdown_path(self) -> Path:
        return self.skill_dir / "SKILL.md"

    def load_skill_instructions(self) -> str:
        try:
            return self.skill_markdown_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            logger.warning("Skill 文件不存在: %s", self.skill_markdown_path)
            return ""

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        module_name = f"skill_{self.skill_dir.name}_{self.definition.phase_name}".replace("-", "_")
        spec = importlib.util.spec_from_file_location(module_name, self.definition.script_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"无法加载 skill 脚本: {self.definition.script_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        fn = getattr(module, self.definition.function_name, None)
        if fn is None:
            raise RuntimeError(f"skill 脚本缺少函数 {self.definition.function_name}: {self.definition.script_path}")

        enriched_context = {
            **context,
            "skill_dir": self.skill_dir,
            "skill_markdown": self.load_skill_instructions(),
            "phase_name": self.definition.phase_name,
        }
        result = fn(enriched_context)
        if inspect.isawaitable(result):
            result = await result
        if not isinstance(result, dict):
            raise RuntimeError(f"skill phase 必须返回 dict: {self.definition.script_path}#{self.definition.function_name}")
        return result


@dataclass
class AgentSkillBundle:
    intent: str
    bundle_name: str
    skill_dir: Path
    metadata: SkillMetadata
    phases: dict[str, ScriptedSkillPhase] = field(default_factory=dict)

    def get_phase(self, phase: str) -> ScriptedSkillPhase:
        if phase not in self.phases:
            raise KeyError(f"Skill bundle {self.bundle_name} 未注册 phase: {phase}")
        return self.phases[phase]

    def resolve_phase(self, confirmed_requirements: Optional[dict[str, Any]] = None) -> str:
        action = str((confirmed_requirements or {}).get("action") or "").strip()
        if self.metadata.confirmation_action and action == self.metadata.confirmation_action and "send" in self.phases:
            return "send"
        return self.metadata.default_phase


class AgentSkillDispatcher:
    """根据 intent 和 phase 分发到 skill bundle。"""

    def __init__(self, bundles: dict[str, AgentSkillBundle]):
        self.bundles = bundles

    def get_bundle(self, intent: str) -> AgentSkillBundle:
        if intent not in self.bundles:
            raise KeyError(f"未找到 intent 对应的 skill bundle: {intent}")
        return self.bundles[intent]

    def dispatch(self, intent: str, phase: str) -> ScriptedSkillPhase:
        return self.get_bundle(intent).get_phase(phase)

    def match_confirmation_action(self, action: str) -> Optional[AgentSkillBundle]:
        for bundle in self.bundles.values():
            if bundle.metadata.confirmation_action == action:
                return bundle
        return None


def parse_skill_metadata(skill_markdown_path: Path) -> Optional[dict[str, str]]:
    try:
        content = skill_markdown_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None

    if not content.startswith("---\n"):
        return None
    parts = content.split("\n---\n", 1)
    if len(parts) != 2:
        return None
    frontmatter = parts[0].removeprefix("---\n")

    data: dict[str, str] = {}
    for line in frontmatter.splitlines():
        stripped = line.strip()
        if not stripped or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        data[key.strip()] = value.strip()

    name = data.get("name", "").strip()
    description = data.get("description", "").strip()
    if not name or not description:
        return None
    return {"name": name, "description": description}


def parse_skill_manifest(skill_dir: Path) -> Optional[SkillMetadata]:
    # 清单文件路径
    manifest_path = skill_dir / "skill.json"
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        logger.warning("Skill manifest 解析失败: %s", exc)
        return None

    name = str(data.get("name") or skill_dir.name).strip()
    intent = str(data.get("intent") or "").strip()
    route = str(data.get("route") or "").strip() or None
    phases = tuple(str(item).strip() for item in data.get("phases") or [] if str(item).strip())
    prerequisites = tuple(str(item).strip() for item in data.get("prerequisites") or [] if str(item).strip())
    default_phase = str(data.get("default_phase") or "").strip() or (phases[0] if phases else "")
    confirmation_action = str(data.get("confirmation_action") or "").strip() or None
    phase_scripts_raw = data.get("phase_scripts") or {}
    if not name or not intent or not phases or not default_phase or not isinstance(phase_scripts_raw, dict):
        return None

    description = ""
    skill_md = parse_skill_metadata(skill_dir / "SKILL.md")
    if skill_md:
        description = skill_md["description"]
    return SkillMetadata(
        name=name,
        description=description,
        intent=intent,
        route=route,
        prerequisites=prerequisites,
        phases=phases,
        default_phase=default_phase,
        confirmation_action=confirmation_action,
    )


def build_skill_bundle_from_directory(skill_dir: Path) -> Optional[AgentSkillBundle]:
    metadata = parse_skill_manifest(skill_dir)
    if not metadata:
        return None

    phases: dict[str, ScriptedSkillPhase] = {}
    for phase in metadata.phases:
        phase_spec = parse_phase_script_spec(skill_dir, phase)
        if not phase_spec:
            logger.warning("Skill %s 缺少 phase 脚本定义: %s", metadata.name, phase)
            continue
        phases[phase] = ScriptedSkillPhase(skill_dir=skill_dir, definition=phase_spec)

    if not phases:
        return None
    return AgentSkillBundle(
        intent=metadata.intent,
        bundle_name=metadata.name,
        skill_dir=skill_dir,
        metadata=metadata,
        phases=phases,
    )


def parse_phase_script_spec(skill_dir: Path, phase: str) -> Optional[SkillPhaseDefinition]:
    manifest_path = skill_dir / "skill.json"
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None

    phase_scripts = data.get("phase_scripts") or {}
    raw = str(phase_scripts.get(phase) or "").strip()
    if not raw or ":" not in raw:
        return None
    rel_path, function_name = raw.split(":", 1)
    return SkillPhaseDefinition(
        phase_name=phase,
        script_path=skill_dir / rel_path.strip(),
        function_name=function_name.strip(),
    )


def build_default_skill_dispatcher(skills_root: Optional[Path] = None) -> AgentSkillDispatcher:
    """自动扫描 skills 目录，构建当前仓库默认的 skill 调度器。"""
    root = Path(skills_root) if skills_root else Path(__file__).resolve().parents[2] / "skills"
    bundles: dict[str, AgentSkillBundle] = {}
    if not root.exists():
        return AgentSkillDispatcher(bundles)

    for skill_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        bundle = build_skill_bundle_from_directory(skill_dir)
        if not bundle:
            continue
        bundles[bundle.intent] = bundle
    return AgentSkillDispatcher(bundles)
