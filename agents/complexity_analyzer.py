from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ComplexityLevel(str, Enum):
    EASY = "EASY"
    HARD = "HARD"


HARD_THRESHOLD = 60


@dataclass
class ComplexityScore:
    score: int
    reasons: list[str] = field(default_factory=list)


@dataclass
class ComplexityResult(ComplexityScore):
    level: ComplexityLevel = ComplexityLevel.EASY
    breakdown: dict[str, int] = field(default_factory=dict)


@dataclass
class TaskFeatures:
    step_count: int = 0
    dependency_count: int = 0
    has_auth: bool = False
    is_e2e: bool = False
    assertion_count: int = 0


class ComplexityAnalyzer:
    WEIGHTS = {
        "step_count": 15,
        "dependency": 10,
        "has_auth": 20,
        "is_e2e": 25,
        "assertion_count": 5,
    }

    AUTH_RE = re.compile(r"\b(auth|jwt|token|login)\b", re.IGNORECASE)
    ASSERT_RE = re.compile(r"\b(assert|verify|check|expect|should|validate|confirm)\b", re.IGNORECASE)

    def analyze(self, task: dict[str, Any] | TaskFeatures) -> ComplexityResult:
        if isinstance(task, TaskFeatures):
            step_count = task.step_count
            dependency_count = task.dependency_count
            has_auth = task.has_auth
            is_e2e = task.is_e2e
            assertion_count = task.assertion_count
            text = ""
        else:
            step_count = len(task.get("steps", task.get("scenarios", [])))
            dependencies = task.get("dependencies", [])
            dependency_count = len(dependencies) if isinstance(dependencies, list) else int(bool(dependencies))
            text = " ".join(str(v) for v in task.values())
            has_auth = bool(self.AUTH_RE.search(text))
            is_e2e = task.get("type") == "e2e"
            assertion_count = len(self.ASSERT_RE.findall(text))

        breakdown = {
            "steps": step_count * self.WEIGHTS["step_count"],
            "dependencies": dependency_count * self.WEIGHTS["dependency"],
            "auth": self.WEIGHTS["has_auth"] if has_auth else 0,
            "e2e": self.WEIGHTS["is_e2e"] if is_e2e else 0,
            "assertions": assertion_count * self.WEIGHTS["assertion_count"],
        }
        score = min(100, sum(breakdown.values()))
        reasons: list[str] = []
        if step_count:
            reasons.append(f"{step_count} steps (+{breakdown['steps']})")
        if dependency_count:
            reasons.append(f"{dependency_count} dependencies (+{breakdown['dependencies']})")
        if has_auth:
            reasons.append("auth/login/token detected (+20)")
        if is_e2e:
            reasons.append("e2e task (+25)")
        if assertion_count:
            reasons.append(f"{assertion_count} assertions (+{breakdown['assertions']})")

        return ComplexityResult(
            score=score,
            reasons=reasons,
            level=ComplexityLevel.HARD if score >= HARD_THRESHOLD else ComplexityLevel.EASY,
            breakdown=breakdown,
        )

    def from_test_description(self, description: str) -> ComplexityResult:
        lowered = description.lower()
        steps = re.findall(r"\b(step|then|next|after|finally|login|search|cart|checkout|payment|track)\b", lowered)
        deps = re.findall(r"\b(depend|require|service|gateway|api|database)\b", lowered)
        task = {
            "type": "e2e" if re.search(r"\b(e2e|journey|flow|complete|full)\b", lowered) else "api",
            "steps": steps or [description],
            "dependencies": deps,
            "name": description,
        }
        return self.analyze(task)
