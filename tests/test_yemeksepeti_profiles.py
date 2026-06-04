from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from agents.complexity_analyzer import ComplexityAnalyzer
from main import app
from mock_api.documentation import YEMEKSEPETI_COMPLETE_DOCS


def test_yemeksepeti_docs_cover_web_and_mobile_surfaces():
    docs = YEMEKSEPETI_COMPLETE_DOCS
    assert docs["product"]["name"] == "Yemeksepeti web and app mirror"
    assert {"Giriş Yap", "Restoran", "Gel Al", "Marketler"}.issubset(set(docs["product"]["public_surfaces"]))
    assert {"android", "ios"} == set(docs["mobile"]["platforms"])
    paths = {endpoint["path"] for endpoint in docs["api"]["endpoints"]}
    assert "/v2/addresses/suggestions" in paths
    assert "/v2/markets/search" in paths
    assert "/v2/coupons/validate" in paths


def test_orchestrator_test_profiles_endpoint():
    client = TestClient(app)
    response = client.get("/api/test-profiles")
    assert response.status_code == 200
    body = response.json()
    profile_ids = {profile["id"] for profile in body["profiles"]}
    assert {"mock", "web-prod-smoke", "mobile-android", "mobile-ios"}.issubset(profile_ids)
    assert {"api", "web", "mobile", "e2e", "prod-smoke"}.issubset(set(body["allowed_test_types"]))


def test_unsupported_test_type_is_rejected():
    client = TestClient(app)
    response = client.post("/api/orchestrate", json={"test_type": "live-order"})
    assert response.status_code == 200
    assert "Unsupported test_type" in response.json()["error"]


def test_mobile_and_real_product_complexity_routes_high():
    analyzer = ComplexityAnalyzer()
    score = analyzer.analyze({
        "type": "mobile",
        "name": "Yemeksepeti Android Appium checkout mirror",
        "steps": ["login", "set address", "open market", "add cart", "checkout"],
        "dependencies": ["appium", "device", "mock api"],
    })
    assert score.score >= 80
    assert any("mobile" in reason for reason in score.reasons)
    assert any("Yemeksepeti" in reason for reason in score.reasons)


def test_appium_capability_files_are_safe_and_parseable():
    for filename, profile in [
        ("capabilities.android.json", "mobile-android"),
        ("capabilities.ios.json", "mobile-ios"),
    ]:
        path = Path("mobile_appium") / filename
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["testProfile"] == profile
        assert data["safeMode"] is True
        assert "appium:app" in data
        assert len(data["scenarios"]) >= 4
