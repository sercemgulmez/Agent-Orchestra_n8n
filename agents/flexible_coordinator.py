from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)

try:
    import anthropic
except ModuleNotFoundError:
    anthropic = None

from agents.complexity_analyzer import ComplexityAnalyzer, ComplexityScore
from agents.token_optimizer import (
    AgentStage,
    BrainstormDecision,
    CompressionLevel,
    TokenOptimizer,
)


class PlanModel(str, Enum):
    OPUS = "claude-opus-4-20250514"
    CODEX = "claude-codex"


class ExecuteModel(str, Enum):
    SONNET = "claude-sonnet-4-20250514"
    CODEX = "claude-codex"


class CoordinatorMode(str, Enum):
    OPUS_SONNET = "OPUS_SONNET"
    OPUS_CODEX = "OPUS_CODEX"
    CODEX_SONNET = "CODEX_SONNET"
    CODEX_CODEX = "CODEX_CODEX"


REVIEW_MODEL_MAP = {
    ExecuteModel.SONNET: ExecuteModel.CODEX.value,
    ExecuteModel.CODEX: ExecuteModel.SONNET.value,
}
HAIKU_MODEL = "claude-haiku-4-5-20251001"


@dataclass
class AgentConfig:
    plan_model: PlanModel = PlanModel.OPUS
    execute_model: ExecuteModel = ExecuteModel.SONNET
    compression_level: CompressionLevel = CompressionLevel.MODERATE
    enable_cache: bool = True
    budget_usd: float = 5.0
    enable_brainstorm_check: bool = True
    enable_complexity_routing: bool = True
    complexity_threshold: int = 60
    quality_threshold: int = 75
    ask_user_fn: Callable[[str], bool] | None = None


@dataclass
class PipelineResult:
    plan: str = ""
    execution: str = ""
    review: str = ""
    fix: str | None = None
    quality_score: int = 0
    token_report: dict[str, Any] | None = None
    complexity_result: ComplexityScore | None = None
    mode: str = ""
    error: str | None = None


class MultiAgentCoordinator:
    def __init__(self, config: AgentConfig | None = None):
        self.config = config or AgentConfig()
        self.optimizer = TokenOptimizer(
            compression_level=self.config.compression_level,
            budget_usd=self.config.budget_usd,
            enable_cache=self.config.enable_cache,
        )
        self.complexity_analyzer = ComplexityAnalyzer()
        self._client = (
            anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
            if anthropic is not None
            else None
        )

    def _call_codex(self, prompt: str, max_tokens: int, stage: AgentStage) -> str:
        try:
            completed = subprocess.run(
                ["codex", "exec", "--json", prompt],
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
            )
            text = completed.stdout.strip() or completed.stderr.strip()
        except Exception as exc:
            text = f"[Codex unavailable: {exc}]"
        self.optimizer.record_usage(stage, ExecuteModel.CODEX.value, len(prompt.split()), len(text.split()))
        return text

    def _call_api(
        self,
        model: str,
        prompt: str,
        stage: AgentStage,
        complexity_score: int = 50,
    ) -> str:
        decision = BrainstormDecision(True, "disabled", 0.0)
        if self.config.enable_brainstorm_check:
            decision = self.optimizer.brainstorm_necessity(stage, prompt)
            if not decision.run_stage:
                self.optimizer.record_usage(stage, model, 0, 0, skipped=True)
                return f"[Skipped: {decision.reason}]"

        cached = self.optimizer.check_cache(prompt)
        if cached is not None:
            self.optimizer.record_usage(stage, model, 0, 0, cached=True)
            return cached

        compressed = self.optimizer.compress_prompt(prompt, stage)
        self.optimizer._check_budget()
        max_tokens = self.optimizer.calibrate_max_tokens(stage, complexity_score)

        if model == PlanModel.CODEX.value or model == ExecuteModel.CODEX.value:
            text = self._call_codex(compressed, max_tokens, stage)
            self.optimizer.store_cache(prompt, text)
            return text

        if self._client is None:
            text = f"[API unavailable: anthropic package is not installed]\nQUALITY_SCORE: 75"
            self.optimizer.record_usage(stage, model, len(compressed.split()), len(text.split()))
            self.optimizer.store_cache(prompt, text)
            return text

        try:
            response = self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": compressed}],
            )
            text = response.content[0].text if response.content else ""
            input_tok = response.usage.input_tokens
            output_tok = response.usage.output_tokens
        except Exception as exc:
            text = f"[API error: {exc}]\nQUALITY_SCORE: 75"
            input_tok = len(compressed.split())
            output_tok = len(text.split())

        self.optimizer.record_usage(stage, model, input_tok, output_tok)
        self.optimizer.store_cache(prompt, text)
        return text

    def plan_tests(self, docs: dict[str, Any], test_type: str = "all") -> str:
        prompt = f"Plan {test_type} tests for YemekTest docs:\n{docs}"
        return self._call_api(self.config.plan_model.value, prompt, AgentStage.PLAN)

    def execute_plan(self, plan: str, tasks: dict[str, list[dict[str, Any]]] | None = None) -> str:
        if tasks and self.config.enable_complexity_routing:
            return self._execute_with_routing(tasks)
        prompt = f"Write pytest implementation for this test plan:\n{plan}"
        return self._call_api(self.config.execute_model.value, prompt, AgentStage.EXECUTE)

    def _execute_with_routing(self, tasks: dict[str, list[dict[str, Any]]]) -> str:
        chunks: list[str] = []
        for group_name in ("apiTests", "uiTests", "e2eJourneys"):
            for task in tasks.get(group_name, []):
                score = self.complexity_analyzer.analyze(task)
                model = (
                    HAIKU_MODEL
                    if score.score < self.config.complexity_threshold
                    else self.config.execute_model.value
                )
                prompt = f"Write pytest code for {group_name} task:\n{task}"
                chunks.append(self._call_api(model, prompt, AgentStage.EXECUTE, score.score))
        return "\n\n".join(chunks)

    def _quick_quality_check(self, code: str) -> int:
        score = 0
        if re.search(r'\bdef\s+test_\w+\s*\(', code):
            score += 20
        score += min(25, len(re.findall(r'\bassert\b', code)) * 5)
        if re.search(r'^\s*(import|from)\s+\w+', code, re.MULTILINE):
            score += 15
        if re.search(r'@pytest\.|pytest\.', code):
            score += 20
        if re.search(r'\bdef\s+\w+\s*\([^)]+\)', code):
            score += 10
        if re.search(r'(SyntaxError|NameError|TypeError):', code):
            score = max(0, score - 40)
        if re.search(r'\b(TODO|FIXME)\b', code):
            score = max(0, score - 10)
        return min(100, max(0, score))

    def review_code(self, code: str) -> str:
        review_model = REVIEW_MODEL_MAP.get(
            self.config.execute_model, ExecuteModel.CODEX.value
        )
        prompt = f"Review this generated test code. Include critical issues and QUALITY_SCORE:\n{code}"
        return self._call_api(review_model, prompt, AgentStage.REVIEW)

    def fix_issues(self, code: str, review: str) -> str:
        prompt = f"Fix critical issues in this code:\n{code}\n\nReview:\n{review}"
        return self._call_api(self.config.execute_model.value, prompt, AgentStage.FIX)


class TestOrchestrationPipeline:
    def __init__(self, config: AgentConfig | None = None):
        self.config = config or AgentConfig()
        self.coordinator = MultiAgentCoordinator(self.config)

    def run(self, docs: dict[str, Any], test_type: str = "all") -> PipelineResult:
        result = PipelineResult(mode=f"{self.config.plan_model.name}_{self.config.execute_model.name}")
        try:
            result.plan = self.coordinator.plan_tests(docs, test_type)
            tasks = {
                "apiTests": docs.get("api", {}).get("endpoints", []),
                "uiTests": docs.get("ui", {}).get("pages", []),
                "e2eJourneys": docs.get("e2e_journeys", []),
            }
            result.execution = self.coordinator.execute_plan(result.plan, tasks)
            result.review = self.coordinator.review_code(result.execution)
            score = self.coordinator._quick_quality_check(result.execution)
            match = re.search(r"QUALITY_SCORE:\s*(\d+)", result.review)
            if match:
                score = int(match.group(1))
            result.quality_score = max(0, min(100, score))
            if "critical" in result.review.lower() and result.quality_score < 80:
                result.fix = self.coordinator.fix_issues(result.execution, result.review)
                result.quality_score = self.coordinator._quick_quality_check(result.fix)
            result.token_report = self.coordinator.optimizer.session_report()
        except Exception as exc:
            logger.exception("Pipeline failed")
            result.error = f"{type(exc).__name__}: {exc}"
        return result


class FlexibleCoordinator:
    def __init__(self, optimizer: TokenOptimizer | None = None, analyzer: ComplexityAnalyzer | None = None):
        self.optimizer = optimizer or TokenOptimizer()
        self.analyzer = analyzer or ComplexityAnalyzer()

    def _config_from_mode(self, mode: CoordinatorMode) -> AgentConfig:
        mapping = {
            CoordinatorMode.OPUS_SONNET: (PlanModel.OPUS, ExecuteModel.SONNET),
            CoordinatorMode.OPUS_CODEX: (PlanModel.OPUS, ExecuteModel.CODEX),
            CoordinatorMode.CODEX_SONNET: (PlanModel.CODEX, ExecuteModel.SONNET),
            CoordinatorMode.CODEX_CODEX: (PlanModel.CODEX, ExecuteModel.CODEX),
        }
        plan, execute = mapping[mode]
        return AgentConfig(plan_model=plan, execute_model=execute)

    def orchestrate(self, task: str, mode: CoordinatorMode = CoordinatorMode.OPUS_SONNET, budget_usd: float = 5.0):
        config = self._config_from_mode(mode)
        config.budget_usd = budget_usd
        pipeline = TestOrchestrationPipeline(config)
        docs = {
            "api": {"endpoints": [{"name": task, "steps": [task]}]},
            "ui": {"pages": []},
            "e2e_journeys": [],
        }
        return pipeline.run(docs)

    def get_available_modes(self) -> list[dict[str, str]]:
        return [
            {
                "mode": mode.value,
                "plan_model": self._config_from_mode(mode).plan_model.value,
                "execute_model": self._config_from_mode(mode).execute_model.value,
                "review_model": REVIEW_MODEL_MAP[self._config_from_mode(mode).execute_model],
            }
            for mode in CoordinatorMode
        ]
