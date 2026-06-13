from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from collections import OrderedDict
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class BudgetExceededError(RuntimeError):
    """Raised when cumulative token spend exceeds the configured budget."""


class AgentStage(str, Enum):
    PLAN = "PLAN"
    EXECUTE = "EXECUTE"
    REVIEW = "REVIEW"
    FIX = "FIX"
    ANALYZE = "ANALYZE"


class CompressionLevel(int, Enum):
    NONE = 0
    LIGHT = 1
    MODERATE = 2
    AGGRESSIVE = 3


MODEL_PRICING: dict[str, dict[str, float]] = {
    "opus": {"input": 15.00, "output": 75.00},
    "sonnet": {"input": 3.00, "output": 15.00},
    "haiku": {"input": 0.80, "output": 4.00},
    "codex": {"input": 3.00, "output": 15.00},
    "claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "claude-codex": {"input": 3.00, "output": 15.00},
}

STAGE_MAX_TOKENS: dict[AgentStage, int] = {
    AgentStage.PLAN: 2500,
    AgentStage.EXECUTE: 6000,
    AgentStage.REVIEW: 2000,
    AgentStage.FIX: 4000,
    AgentStage.ANALYZE: 1500,
}


@dataclass
class TokenUsage:
    stage: AgentStage
    model: str
    input_tok: int
    output_tok: int
    cost_usd: float
    cached: bool = False
    skipped: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class BrainstormDecision:
    run_stage: bool
    reason: str
    savings_est: float


@dataclass
class GraphNode:
    id: str
    label: str
    model: str
    total_tok: int
    total_cost: float
    call_count: int


@dataclass
class GraphEdge:
    source: str
    target: str
    tokens_passed: int
    weight: float


@dataclass
class ProfileRule:
    id: str
    description: str
    keywords: list[str]
    weight: int
    priority: str = "normal"


@dataclass
class ProjectProfile:
    id: str
    name: str
    summary: str
    rules: list[ProfileRule]


@dataclass
class ProfileAnalysis:
    profile_id: str
    score: int
    matched_rules: list[str]
    missing_rules: list[str]
    savings_est: float
    compressed_preview: str = ""


OBSIDIAN_MAPS_PROFILE = ProjectProfile(
    id="obsidian-maps",
    name="Obsidian Maps",
    summary=(
        "Local-first Obsidian plugin profile for map-view features with privacy, "
        "stable commands, lazy startup, strict TypeScript, and release artifact discipline."
    ),
    rules=[
        ProfileRule(
            "local_first",
            "Default to local/offline operation and avoid network calls unless clearly user-facing.",
            ["local", "offline", "network", "tile", "external service"],
            18,
            "high",
        ),
        ProfileRule(
            "no_hidden_telemetry",
            "Do not include hidden telemetry; require explicit opt-in for analytics.",
            ["telemetry", "analytics", "opt-in", "privacy"],
            18,
            "high",
        ),
        ProfileRule(
            "stable_commands",
            "Register user-facing commands with stable IDs.",
            ["addCommand", "command", "stable id", "open-map-view"],
            12,
        ),
        ProfileRule(
            "settings_persistence",
            "Provide defaults, validation, loadData, and saveData for settings.",
            ["settings", "defaults", "loadData", "saveData", "validation"],
            12,
        ),
        ProfileRule(
            "lazy_startup",
            "Keep plugin startup light and defer map work until a command/view is opened.",
            ["lazy", "defer", "startup", "onload", "light"],
            12,
        ),
        ProfileRule(
            "cleanup_lifecycle",
            "Use Obsidian register helpers for events, DOM listeners, and intervals.",
            ["registerEvent", "registerDomEvent", "registerInterval", "cleanup"],
            10,
        ),
        ProfileRule(
            "strict_typescript",
            "Prefer strict TypeScript with clear module boundaries.",
            ["typescript", "strict", "src/", "types"],
            10,
        ),
        ProfileRule(
            "release_artifacts",
            "Build release artifacts main.js, manifest.json, and optional styles.css at plugin root.",
            ["main.js", "manifest.json", "styles.css", "versions.json", "release"],
            8,
        ),
    ],
)

PROJECT_PROFILES = {OBSIDIAN_MAPS_PROFILE.id: OBSIDIAN_MAPS_PROFILE}


class TokenGraphTracker:
    DATA_FILE = Path("token_optimizer_data.json")

    def __init__(self, data_file: Path | str | None = None):
        self.DATA_FILE = Path(data_file) if data_file else self.DATA_FILE
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []
        self._last_stage: str | None = None
        self._load()

    def reset(self) -> None:
        self._nodes = {}
        self._edges = []
        self._last_stage = None

    def _model_label(self, model: str) -> str:
        parts = model.split("-")
        return parts[1] if "-" in model and len(parts) > 1 else model

    def _get_or_create_node(self, stage: AgentStage, model: str) -> GraphNode:
        model_label = self._model_label(model)
        node_id = f"{stage.value}:{model_label}"
        if node_id not in self._nodes:
            self._nodes[node_id] = GraphNode(
                id=node_id,
                label=stage.value,
                model=model,
                total_tok=0,
                total_cost=0.0,
                call_count=0,
            )
        return self._nodes[node_id]

    def record(self, usage: TokenUsage) -> None:
        node = self._get_or_create_node(usage.stage, usage.model)
        total = usage.input_tok + usage.output_tok
        node.total_tok += total
        node.total_cost += usage.cost_usd
        node.call_count += 1

        if self._last_stage and self._last_stage != node.id:
            self._edges.append(
                GraphEdge(
                    source=self._last_stage,
                    target=node.id,
                    tokens_passed=usage.input_tok,
                    weight=max(total, 1) / 1000,
                )
            )
        self._last_stage = node.id

    def graph_dict(self) -> dict[str, list[dict[str, Any]]]:
        return {
            "nodes": [asdict(node) for node in self._nodes.values()],
            "edges": [asdict(edge) for edge in self._edges],
        }

    def to_dict(self) -> dict[str, list[dict[str, Any]]]:
        return self.graph_dict()

    def render_ascii(self) -> str:
        if not self._nodes:
            return "(empty graph)"
        lines = ["TOKEN FLOW GRAPH"]
        for node in self._nodes.values():
            lines.append(
                f"[{node.id}] {node.total_tok} tok | ${node.total_cost:.6f} | calls={node.call_count}"
            )
        for edge in self._edges:
            lines.append(f"{edge.source} -> {edge.target} ({edge.tokens_passed} tok)")
        return "\n".join(lines)

    def _save(self) -> None:
        payload = self.graph_dict()
        self.DATA_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _load(self) -> None:
        if not self.DATA_FILE.exists():
            return
        try:
            raw = json.loads(self.DATA_FILE.read_text(encoding="utf-8"))
            self._nodes = {n["id"]: GraphNode(**n) for n in raw.get("nodes", [])}
            self._edges = [GraphEdge(**e) for e in raw.get("edges", [])]
        except Exception:
            self.reset()


class TokenOptimizer:
    def __init__(
        self,
        compression_level: CompressionLevel = CompressionLevel.MODERATE,
        budget_usd: float = 5.0,
        data_path: str = "token_optimizer_data.json",
        enable_cache: bool = True,
        cache_maxsize: int = 500,
    ):
        self.compression_level = compression_level
        self.budget_usd = budget_usd
        self.enable_cache = enable_cache
        self._cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._cache_maxsize = cache_maxsize
        self._usage: list[TokenUsage] = []
        self._graph = TokenGraphTracker(data_path)
        self._cache_hits = 0
        self._profile_reports: dict[str, ProfileAnalysis] = {}

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _pricing_for(self, model: str) -> dict[str, float]:
        if model in MODEL_PRICING:
            return MODEL_PRICING[model]
        lowered = model.lower()
        for key, pricing in MODEL_PRICING.items():
            if key in lowered:
                return pricing
        return MODEL_PRICING["sonnet"]

    def _recent_same_context(self, ctx_hash: str, window_seconds: int = 300) -> bool:
        cutoff = time.time() - window_seconds
        return any(
            item.get("ctx_hash") == ctx_hash and item.get("timestamp", 0) >= cutoff
            for item in self._cache.values()
        )

    def brainstorm_necessity(self, stage: AgentStage, prompt: str) -> BrainstormDecision:
        cache_key = self._hash(f"{stage.value}:{prompt}")
        if self._recent_same_context(cache_key):
            return BrainstormDecision(False, "same context seen in last 5 minutes", 0.20)
        if len(prompt.split()) < 12 and stage != AgentStage.EXECUTE:
            return BrainstormDecision(False, "short prompt does not need brainstorm", 0.10)
        return BrainstormDecision(True, "stage should run", 0.0)

    def compress_prompt(self, prompt: str, stage: AgentStage | None = None) -> str:
        level = self.compression_level
        if level == CompressionLevel.NONE:
            return prompt

        result = " ".join(prompt.split())
        if level == CompressionLevel.LIGHT:
            return result

        filler_patterns = [
            r"\b[Pp]lease make sure to\b",
            r"\b[Mm]ake sure to\b",
            r"\b[Nn]ote that\b",
            r"\b[Yy]ou should\b",
            r"\b[Ii]t is important to note that\b",
            r"\b[Ii]n order to\b",
        ]
        for pattern in filler_patterns:
            result = re.sub(pattern, "", result)
        result = re.sub(r"\s+", " ", result).strip()

        def trim_array(match: re.Match[str]) -> str:
            text = match.group(0)
            parts = [part.strip() for part in text[1:-1].split(",")]
            if len(parts) <= 8:
                return text
            return "[" + ", ".join(parts[:8]) + ", ...]"

        result = re.sub(r"\[[^\[\]]{80,}\]", trim_array, result)
        if level == CompressionLevel.MODERATE:
            return result

        def minify_json(match: re.Match[str]) -> str:
            try:
                return json.dumps(json.loads(match.group(0)), separators=(",", ":"))
            except Exception:
                return match.group(0)

        result = re.sub(r"\{[^{}]{20,}\}", minify_json, result)

        def truncate_code(match: re.Match[str]) -> str:
            lang = match.group(1) or ""
            lines = match.group(2).splitlines()
            if len(lines) <= 30:
                return match.group(0)
            return f"```{lang}\n" + "\n".join(lines[:30]) + "\n# ... truncated\n```"

        return re.sub(r"```(\w*)\n(.*?)```", truncate_code, result, flags=re.DOTALL).strip()

    def available_profiles(self) -> list[dict[str, Any]]:
        return [
            {
                "id": profile.id,
                "name": profile.name,
                "summary": profile.summary,
                "rules": [asdict(rule) for rule in profile.rules],
            }
            for profile in PROJECT_PROFILES.values()
        ]

    def _profile_for(self, profile_id: str) -> ProjectProfile:
        try:
            return PROJECT_PROFILES[profile_id]
        except KeyError as exc:
            raise ValueError(f"Unknown project profile: {profile_id}") from exc

    def analyze_project_profile(self, profile_id: str, content: str) -> ProfileAnalysis:
        profile = self._profile_for(profile_id)
        lowered = content.lower()
        matched: list[str] = []
        missing: list[str] = []
        score = 0
        max_score = sum(rule.weight for rule in profile.rules)

        for rule in profile.rules:
            if any(keyword.lower() in lowered for keyword in rule.keywords):
                matched.append(rule.id)
                score += rule.weight
            else:
                missing.append(rule.id)

        normalized = round((score / max(max_score, 1)) * 100)
        compressed = self.compress_with_profile(content, profile_id, AgentStage.ANALYZE)
        savings = 1 - (len(compressed) / max(len(content), 1))
        analysis = ProfileAnalysis(
            profile_id=profile_id,
            score=normalized,
            matched_rules=matched,
            missing_rules=missing,
            savings_est=round(max(0.0, savings), 3),
            compressed_preview=compressed[:500],
        )
        self._profile_reports[profile_id] = analysis
        return analysis

    def compress_with_profile(
        self,
        prompt: str,
        profile_id: str = "obsidian-maps",
        stage: AgentStage | None = None,
    ) -> str:
        profile = self._profile_for(profile_id)
        compressed = self.compress_prompt(prompt, stage)
        high_rules = [rule.description for rule in profile.rules if rule.priority == "high"]
        guardrails = " ".join(f"[{profile.id}:{idx + 1}] {rule}" for idx, rule in enumerate(high_rules))
        if guardrails and guardrails not in compressed:
            return f"{guardrails}\n\n{compressed}".strip()
        return compressed

    def _cache_get(self, key: str) -> dict[str, Any] | None:
        if key not in self._cache:
            return None
        self._cache.move_to_end(key)
        return self._cache[key]

    def _cache_set(self, key: str, value: dict[str, Any]) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self._cache_maxsize:
            self._cache.popitem(last=False)

    def check_cache(self, prompt: str) -> str | None:
        if not self.enable_cache:
            return None
        key = self._hash(prompt)
        item = self._cache_get(key)
        if not item:
            return None
        self._cache_hits += 1
        return item.get("response")

    def store_cache(self, prompt: str, response: str) -> None:
        if not self.enable_cache:
            return
        key = self._hash(prompt)
        self._cache_set(key, {
            "response": response,
            "ctx_hash": key,
            "timestamp": time.time(),
        })

    def calibrate_max_tokens(self, stage: AgentStage, complexity_score: int = 50) -> int:
        base = STAGE_MAX_TOKENS.get(stage, 2000)
        if complexity_score < 30:
            return min(base, 1024)
        if complexity_score < 60:
            return min(base, 2048)
        return base

    def record_usage(
        self,
        stage: AgentStage,
        model: str,
        input_tok: int,
        output_tok: int,
        cached: bool = False,
        skipped: bool = False,
    ) -> TokenUsage:
        pricing = self._pricing_for(model)
        cost = (input_tok * pricing["input"] + output_tok * pricing["output"]) / 1_000_000
        usage = TokenUsage(stage, model, input_tok, output_tok, cost, cached, skipped)
        self._usage.append(usage)
        self._graph.record(usage)
        self._check_budget()
        return usage

    def _check_budget(self) -> None:
        if not self.budget_usd:
            return
        total = sum(item.cost_usd for item in self._usage)
        if total >= self.budget_usd:
            raise BudgetExceededError(
                f"Budget exhausted: spent ${total:.4f} of ${self.budget_usd:.2f}"
            )
        if total >= self.budget_usd * 0.90:
            logger.warning(
                "Token budget at %d%%: $%.4f remaining",
                int(total / self.budget_usd * 100),
                self.budget_usd - total,
            )

    def session_report(self) -> dict[str, Any]:
        total_in = sum(item.input_tok for item in self._usage)
        total_out = sum(item.output_tok for item in self._usage)
        total_cost = sum(item.cost_usd for item in self._usage)
        stage_breakdown: dict[str, dict[str, Any]] = {}
        for item in self._usage:
            key = item.stage.value
            stage_breakdown.setdefault(
                key, {"tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0, "calls": 0}
            )
            stage_breakdown[key]["tokens_in"] += item.input_tok
            stage_breakdown[key]["tokens_out"] += item.output_tok
            stage_breakdown[key]["cost_usd"] += item.cost_usd
            stage_breakdown[key]["calls"] += 1

        return {
            "api_calls": len([u for u in self._usage if not u.cached and not u.skipped]),
            "cache_hits": self._cache_hits,
            "cache_hit_rate": round(self._cache_hits / max(self._cache_hits + len(self._usage), 1), 3),
            "total_tokens_in": total_in,
            "total_tokens_out": total_out,
            "total_tokens": total_in + total_out,
            "total_cost_usd": round(total_cost, 6),
            "stage_breakdown": stage_breakdown,
            "graph_ascii": self._graph.render_ascii(),
            "node_count": len(self._graph.graph_dict()["nodes"]),
            "profiles": {
                key: asdict(value)
                for key, value in self._profile_reports.items()
            },
        }

    def graph_dict(self) -> dict[str, list[dict[str, Any]]]:
        return self._graph.graph_dict()

    def reset_session(self) -> None:
        self._usage = []
        self._cache_hits = 0
        self._graph.reset()
        self._profile_reports = {}

    def loadData(self) -> None:
        self._graph._load()

    def saveData(self) -> None:
        self._graph._save()

    # Backward-compatible names used by the existing server code.
    def compress(self, prompt: str, level: CompressionLevel) -> str:
        old = self.compression_level
        self.compression_level = level
        try:
            return self.compress_prompt(prompt)
        finally:
            self.compression_level = old

    def brainstorm_check(self, prompt: str) -> tuple[bool, str | None]:
        cached = self.check_cache(prompt)
        return cached is not None, cached

    def cache_write(self, prompt: str, response: str) -> None:
        self.store_cache(prompt, response)

    def record_node(self, stage: AgentStage, tokens_in: int, tokens_out: int, model: str) -> str:
        usage = self.record_usage(stage, model, tokens_in, tokens_out)
        return f"{usage.stage.value}:{usage.model}:{int(usage.timestamp * 1000)}"

    def generate_session_report(self) -> dict[str, Any]:
        return self.session_report()

    def get_graph(self) -> TokenGraphTracker:
        return self._graph


OPUS = MODEL_PRICING["opus"]
SONNET = MODEL_PRICING["sonnet"]
HAIKU = MODEL_PRICING["haiku"]
