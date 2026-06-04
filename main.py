from __future__ import annotations

import time
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from typing import Any, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from agents.complexity_analyzer import ComplexityAnalyzer
from agents.flexible_coordinator import (
    AgentConfig,
    ExecuteModel,
    PlanModel,
    REVIEW_MODEL_MAP,
    TestOrchestrationPipeline,
)
from agents.token_optimizer import AgentStage, CompressionLevel, TokenOptimizer
from mock_api.documentation import YEMEKSEPETI_COMPLETE_DOCS

load_dotenv()

TEST_PROFILES = {
    "mock": {
        "id": "mock",
        "target": "local mirror",
        "base_url": "http://localhost:8000",
        "allows_side_effects": True,
        "test_types": ["api", "web", "mobile", "e2e"],
        "forbidden_actions": [],
        "safe_examples": [
            "checkout order tracking in mirror",
            "login with test account in mirror",
            "add cart and coupon in mock",
        ],
    },
    "web-prod-smoke": {
        "id": "web-prod-smoke",
        "target": "https://www.yemeksepeti.com/",
        "base_url": "https://www.yemeksepeti.com/",
        "allows_side_effects": False,
        "test_types": ["prod-smoke"],
        "forbidden_actions": ["login submit", "cart", "checkout", "payment", "order", "coupon", "personal data"],
        "safe_examples": [
            "homepage loads",
            "public navigation tabs visible",
            "language toggle visible",
            "static smoke no account no cart no payment",
        ],
    },
    "mobile-android": {
        "id": "mobile-android",
        "target": "Appium Android",
        "base_url": "env:YEMEKSEPETI_ANDROID_APP",
        "allows_side_effects": False,
        "test_types": ["mobile"],
        "forbidden_actions": ["login submit", "cart", "checkout", "payment", "order", "coupon", "personal data"],
        "safe_examples": [
            "open app and verify login entry",
            "public onboarding smoke",
            "surface tabs visible without checkout",
        ],
    },
    "mobile-ios": {
        "id": "mobile-ios",
        "target": "Appium iOS",
        "base_url": "env:YEMEKSEPETI_IOS_APP",
        "allows_side_effects": False,
        "test_types": ["mobile"],
        "forbidden_actions": ["login submit", "cart", "checkout", "payment", "order", "coupon", "personal data"],
        "safe_examples": [
            "open app and verify login entry",
            "public onboarding smoke",
            "surface tabs visible without checkout",
        ],
    },
}

ALLOWED_TEST_TYPES = {"api", "web", "mobile", "e2e", "prod-smoke", "all"}
FORBIDDEN_SIDE_EFFECT_PATTERNS = {
    "order": ["order", "sipariş", "create order", "/orders/create"],
    "checkout": ["checkout"],
    "payment": ["payment", "ödeme", "pay order", "pay"],
    "cart": ["cart", "sepet", "/cart/add", "add to cart"],
    "coupon": ["coupon", "kupon"],
    "login_submit": ["login with account", "submit login", "real account", "credential"],
    "personal_data": ["phone", "telefon", "credit card", "kredi kart", "personal address", "kişisel adres"],
}


@dataclass
class SafetyViolation:
    code: str
    message: str
    matched: str


@dataclass
class SafetyPolicy:
    profile_id: str
    allows_side_effects: bool
    allowed_test_types: list[str]
    forbidden_actions: list[str]
    safe_examples: list[str]

    @classmethod
    def from_profile(cls, profile: dict[str, Any]) -> "SafetyPolicy":
        return cls(
            profile_id=profile["id"],
            allows_side_effects=profile["allows_side_effects"],
            allowed_test_types=profile["test_types"],
            forbidden_actions=profile.get("forbidden_actions", []),
            safe_examples=profile.get("safe_examples", []),
        )


def _profile_policy(profile: dict[str, Any]) -> SafetyPolicy:
    return SafetyPolicy.from_profile(profile)


def _scan_forbidden_actions(text: str) -> list[SafetyViolation]:
    lowered = text.lower()
    violations: list[SafetyViolation] = []
    for code, patterns in FORBIDDEN_SIDE_EFFECT_PATTERNS.items():
        for pattern in patterns:
            if pattern in lowered:
                violations.append(
                    SafetyViolation(
                        code=code,
                        message=f"Side-effect action is not allowed in non-mock profiles: {code}",
                        matched=pattern,
                    )
                )
                break
    return violations


def _validate_safety(req: "OrchestrateRequest", profile: dict[str, Any]) -> list[SafetyViolation]:
    policy = _profile_policy(profile)
    violations: list[SafetyViolation] = []
    if req.test_type not in policy.allowed_test_types:
        violations.append(
            SafetyViolation(
                code="test_type_not_allowed",
                message=f"{policy.profile_id} only allows: {', '.join(policy.allowed_test_types)}",
                matched=req.test_type,
            )
        )
    if not policy.allows_side_effects:
        text = " ".join(
            str(value)
            for value in [req.test_type, req.task, req.profile]
            if value is not None
        )
        violations.extend(_scan_forbidden_actions(text))
    return violations


def _safety_error(profile: dict[str, Any], violations: list[SafetyViolation]) -> dict[str, Any]:
    policy = _profile_policy(profile)
    return {
        "error": "Safety policy violation",
        "violations": [asdict(violation) for violation in violations],
        "allowed_profile": {
            "id": policy.profile_id,
            "allowed_test_types": policy.allowed_test_types,
            "allows_side_effects": policy.allows_side_effects,
        },
        "safe_alternative": (
            "Use profile=mock for cart, checkout, coupon, payment, login-submit, and order flows. "
            f"For {policy.profile_id}, use examples: {', '.join(policy.safe_examples)}."
        ),
    }

_optimizer = TokenOptimizer(data_path="token_optimizer_data.json")
_analyzer = ComplexityAnalyzer()
_last_result: dict[str, Any] | None = None
_start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _optimizer.loadData()
    yield
    _optimizer.saveData()


app = FastAPI(
    title="YemekTest Orchestrator",
    version="2.0.0",
    description="AI-powered test orchestration platform for Yemeksepeti mock app",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class OrchestrateRequest(BaseModel):
    plan_model: Any = PlanModel.OPUS
    execute_model: Any = ExecuteModel.SONNET
    test_type: str = "all"
    compression: Any = CompressionLevel.MODERATE
    budget: float = Field(default=5.0, alias="budget_usd")
    routing: bool = True
    task: Optional[str] = None
    mode: Optional[str] = None
    profile: str = "mock"

    model_config = {"populate_by_name": True}


class ProfileAnalyzeRequest(BaseModel):
    content: str


class ProfileCompressRequest(BaseModel):
    prompt: str
    stage: str = "ANALYZE"


def _compression_from(value: str | int | CompressionLevel) -> CompressionLevel:
    if isinstance(value, CompressionLevel):
        return value
    if isinstance(value, int):
        return CompressionLevel(value)
    if str(value).isdigit():
        return CompressionLevel(int(value))
    return CompressionLevel[value.upper()]


def _plan_model_from(value: Any) -> PlanModel:
    if isinstance(value, PlanModel):
        return value
    text = str(value)
    if text in PlanModel._value2member_map_:
        return PlanModel(text)
    return PlanModel[text.upper()]


def _execute_model_from(value: Any) -> ExecuteModel:
    if isinstance(value, ExecuteModel):
        return value
    text = str(value)
    if text in ExecuteModel._value2member_map_:
        return ExecuteModel(text)
    return ExecuteModel[text.upper()]


def _models_from_mode(mode: Optional[str]) -> tuple[PlanModel, ExecuteModel] | None:
    if not mode:
        return None
    mapping = {
        "OPUS_SONNET": (PlanModel.OPUS, ExecuteModel.SONNET),
        "OPUS_CODEX": (PlanModel.OPUS, ExecuteModel.CODEX),
        "CODEX_SONNET": (PlanModel.CODEX, ExecuteModel.SONNET),
        "CODEX_CODEX": (PlanModel.CODEX, ExecuteModel.CODEX),
    }
    return mapping.get(mode.upper())


@app.get("/")
async def root():
    return {"status": "ok", "version": "2.0"}


@app.post("/api/orchestrate")
async def orchestrate(req: OrchestrateRequest):
    global _last_result
    if req.test_type not in ALLOWED_TEST_TYPES:
        return {"error": f"Unsupported test_type: {req.test_type}", "allowed": sorted(ALLOWED_TEST_TYPES)}
    if req.profile not in TEST_PROFILES:
        return {"error": f"Unsupported profile: {req.profile}", "allowed_profiles": sorted(TEST_PROFILES)}
    profile = TEST_PROFILES[req.profile]
    violations = _validate_safety(req, profile)
    if violations:
        return _safety_error(profile, violations)
    mode_models = _models_from_mode(req.mode)
    plan_model, execute_model = mode_models or (
        _plan_model_from(req.plan_model),
        _execute_model_from(req.execute_model),
    )
    config = AgentConfig(
        plan_model=plan_model,
        execute_model=execute_model,
        compression_level=_compression_from(req.compression),
        budget_usd=req.budget,
        enable_complexity_routing=req.routing,
    )
    pipeline = TestOrchestrationPipeline(config)
    docs = dict(YEMEKSEPETI_COMPLETE_DOCS)
    docs["active_profile"] = profile
    if req.task:
        docs["requested_task"] = req.task
    result = pipeline.run(docs, req.test_type)
    report = result.token_report or pipeline.coordinator.optimizer.session_report()
    _last_result = {
        "plan": result.plan,
        "execution": result.execution,
        "review": result.review,
        "fix": result.fix,
        "quality_score": result.quality_score,
        "token_report": report,
        "error": result.error,
        "finalScore": result.quality_score,
        "mode": result.mode,
        "test_type": req.test_type,
        "profile": profile,
        "scenario_scope": {
            "api_endpoints": len(docs.get("api", {}).get("endpoints", [])),
            "ui_pages": len(docs.get("ui", {}).get("pages", [])),
            "e2e_journeys": len(docs.get("e2e_journeys", [])),
            "mobile_platforms": docs.get("mobile", {}).get("platforms", []),
        },
    }
    return _last_result


@app.get("/api/token-report")
async def token_report():
    if _last_result and _last_result.get("token_report"):
        return _last_result["token_report"]
    return _optimizer.session_report()


@app.get("/api/graph")
async def get_graph():
    return _optimizer.graph_dict()


@app.get("/api/modes")
async def get_modes():
    combinations = []
    for plan_model in PlanModel:
        for execute_model in ExecuteModel:
            combinations.append(
                {
                    "plan_model": plan_model.value,
                    "execute_model": execute_model.value,
                    "review_model": REVIEW_MODEL_MAP[execute_model],
                    "name": f"{plan_model.name}_{execute_model.name}",
                }
            )
    return {"combinations": combinations}


@app.get("/api/status")
async def get_status():
    return {
        "status": "ok",
        "version": "2.0",
        "uptime_seconds": round(time.time() - _start_time, 1),
        "last_score": (_last_result or {}).get("quality_score"),
        "last_profile": (_last_result or {}).get("profile"),
        "last_test_type": (_last_result or {}).get("test_type"),
        "service": "yemektest-orchestrator",
    }


@app.get("/api/test-profiles")
async def test_profiles():
    return {
        "profiles": [
            {
                **profile,
                "allowed_test_types": profile["test_types"],
                "safety_policy": asdict(_profile_policy(profile)),
            }
            for profile in TEST_PROFILES.values()
        ],
        "allowed_test_types": sorted(ALLOWED_TEST_TYPES),
        "safe_testing_policy": "Live prod only supports read-only smoke checks. Login, cart, checkout, and mobile flows use mock/staging test accounts.",
    }


@app.get("/api/complexity/analyze")
async def analyze_complexity(task: str = Query(..., description="Task description to analyze")):
    result = _analyzer.from_test_description(task)
    return {
        "score": result.score,
        "level": result.level.value,
        "reasons": result.reasons,
        "breakdown": result.breakdown,
        "recommended_model": "haiku" if result.score < 60 else "sonnet",
    }


@app.get("/api/token-profiles")
async def token_profiles():
    return {"profiles": _optimizer.available_profiles()}


@app.post("/api/token-profiles/obsidian-maps/analyze")
async def analyze_obsidian_maps_profile(req: ProfileAnalyzeRequest):
    analysis = _optimizer.analyze_project_profile("obsidian-maps", req.content)
    return {
        "profile_id": analysis.profile_id,
        "score": analysis.score,
        "matched_rules": analysis.matched_rules,
        "missing_rules": analysis.missing_rules,
        "savings_est": analysis.savings_est,
        "compressed_preview": analysis.compressed_preview,
    }


@app.post("/api/token-profiles/obsidian-maps/compress")
async def compress_obsidian_maps_profile(req: ProfileCompressRequest):
    stage = AgentStage[req.stage.upper()]
    compressed = _optimizer.compress_with_profile(req.prompt, "obsidian-maps", stage)
    analysis = _optimizer.analyze_project_profile("obsidian-maps", req.prompt)
    return {
        "profile_id": "obsidian-maps",
        "stage": stage.value,
        "original_length": len(req.prompt),
        "compressed_length": len(compressed),
        "savings_est": round(1 - (len(compressed) / max(len(req.prompt), 1)), 3),
        "compressed": compressed,
        "analysis": {
            "score": analysis.score,
            "matched_rules": analysis.matched_rules,
            "missing_rules": analysis.missing_rules,
        },
    }


_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>YemekTest Hub Dashboard</title>
  <style>
    body { margin: 0; font-family: system-ui, sans-serif; background: #f8fafc; color: #111827; }
    header { padding: 20px 28px; background: #e63946; color: white; }
    main { padding: 24px 28px; display: grid; gap: 16px; }
    section { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; }
    pre { white-space: pre-wrap; background: #f1f5f9; padding: 12px; border-radius: 6px; }
  </style>
</head>
<body>
  <header><h1>YemekTest Hub</h1></header>
  <main>
    <section><h2>Status</h2><pre id="status">Loading...</pre></section>
    <section><h2>Test profile</h2><pre id="test-profile">Loading...</pre></section>
    <section><h2>Modes</h2><pre id="modes">Loading...</pre></section>
    <section><h2>Token Graph</h2><pre id="graph">Loading...</pre></section>
    <section><h2>Obsidian Maps profile</h2><pre id="obsidian-profile">Loading...</pre></section>
  </main>
  <script>
    async function load() {
      const [status, profiles, modes, graph, report] = await Promise.all([
        fetch('/api/status').then(r => r.json()),
        fetch('/api/test-profiles').then(r => r.json()),
        fetch('/api/modes').then(r => r.json()),
        fetch('/api/graph').then(r => r.json()),
        fetch('/api/token-report').then(r => r.json())
      ]);
      document.getElementById('status').textContent = JSON.stringify(status, null, 2);
      document.getElementById('test-profile').textContent = JSON.stringify(profiles, null, 2);
      document.getElementById('modes').textContent = JSON.stringify(modes, null, 2);
      document.getElementById('graph').textContent = JSON.stringify(graph, null, 2);
      document.getElementById('obsidian-profile').textContent = JSON.stringify(report.profiles?.['obsidian-maps'] || {
        message: 'No Obsidian Maps profile analysis yet. POST /api/token-profiles/obsidian-maps/analyze to populate this panel.'
      }, null, 2);
    }
    load();
  </script>
</body>
</html>
"""


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return _DASHBOARD_HTML


@app.get("/health")
async def health():
    return {"status": "ok", "service": "orchestrator"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
