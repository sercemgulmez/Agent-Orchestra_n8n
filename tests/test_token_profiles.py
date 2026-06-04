from __future__ import annotations

from fastapi.testclient import TestClient

from agents.token_optimizer import AgentStage, TokenOptimizer, ProfileAnalysis, ProjectProfile, ProfileRule
from main import app


def test_obsidian_maps_profile_analysis_scores_compliant_content():
    opt = TokenOptimizer()
    content = """
    This Obsidian plugin is local-first and offline by default. It has no hidden
    telemetry or analytics. Commands use stable ids via addCommand, settings use
    loadData and saveData defaults, startup is lazy, and release artifacts include
    main.js, manifest.json, styles.css, and versions.json.
    """
    analysis = opt.analyze_project_profile("obsidian-maps", content)
    assert isinstance(analysis, ProfileAnalysis)
    assert analysis.score >= 80
    assert "local_first" in analysis.matched_rules
    assert "no_hidden_telemetry" in analysis.matched_rules


def test_obsidian_maps_profile_analysis_reports_missing_rules():
    opt = TokenOptimizer()
    analysis = opt.analyze_project_profile("obsidian-maps", "Draw a map.")
    assert analysis.score < 40
    assert "local_first" in analysis.missing_rules
    assert "no_hidden_telemetry" in analysis.missing_rules


def test_compress_with_profile_preserves_high_priority_guardrails():
    opt = TokenOptimizer()
    prompt = "Please make sure to build a map command. Note that you should keep it small."
    compressed = opt.compress_with_profile(prompt, "obsidian-maps", AgentStage.PLAN)
    assert len(compressed) < len(prompt) + 260
    assert "local/offline" in compressed
    assert "hidden telemetry" in compressed
    assert "Please make sure" not in compressed


def test_token_profile_fastapi_endpoints_and_report():
    client = TestClient(app)

    profiles = client.get("/api/token-profiles")
    assert profiles.status_code == 200
    assert profiles.json()["profiles"][0]["id"] == "obsidian-maps"

    analyze = client.post(
        "/api/token-profiles/obsidian-maps/analyze",
        json={"content": "local offline telemetry opt-in addCommand loadData saveData main.js manifest.json"},
    )
    assert analyze.status_code == 200
    assert analyze.json()["score"] > 50

    compress = client.post(
        "/api/token-profiles/obsidian-maps/compress",
        json={"prompt": "Please make sure to avoid telemetry and keep startup lazy.", "stage": "PLAN"},
    )
    assert compress.status_code == 200
    assert "compressed" in compress.json()

    report = client.get("/api/token-report")
    assert report.status_code == 200
    assert "obsidian-maps" in report.json()["profiles"]


def test_profile_dataclasses_importable():
    rule = ProfileRule("x", "Example", ["example"], 1)
    profile = ProjectProfile("demo", "Demo", "Summary", [rule])
    assert profile.rules[0].id == "x"
