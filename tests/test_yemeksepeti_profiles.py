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
    web_profile = next(profile for profile in body["profiles"] if profile["id"] == "web-prod-smoke")
    assert web_profile["allowed_test_types"] == ["prod-smoke"]
    assert "checkout" in web_profile["forbidden_actions"]


def test_unsupported_test_type_is_rejected():
    client = TestClient(app)
    response = client.post("/api/orchestrate", json={"test_type": "live-order"})
    assert response.status_code == 200
    assert "Unsupported test_type" in response.json()["error"]


def test_web_prod_smoke_rejects_e2e():
    client = TestClient(app)
    response = client.post(
        "/api/orchestrate",
        json={"profile": "web-prod-smoke", "test_type": "e2e", "task": "public homepage"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["error"] == "Safety policy violation"
    assert body["violations"][0]["code"] == "test_type_not_allowed"


def test_web_prod_smoke_allows_read_only_public_navigation():
    client = TestClient(app)
    response = client.post(
        "/api/orchestrate",
        json={
            "profile": "web-prod-smoke",
            "test_type": "prod-smoke",
            "task": "homepage public tabs visible and language toggle visible",
            "mode": "OPUS_SONNET",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body.get("error") != "Safety policy violation"
    assert body["profile"]["id"] == "web-prod-smoke"


def test_web_prod_smoke_rejects_checkout_payment_order_text():
    client = TestClient(app)
    response = client.post(
        "/api/orchestrate",
        json={"profile": "web-prod-smoke", "test_type": "prod-smoke", "task": "checkout and pay order"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["error"] == "Safety policy violation"
    codes = {violation["code"] for violation in body["violations"]}
    assert {"checkout", "payment", "order"}.issubset(codes)


def test_mobile_profile_rejects_cart_checkout_actions():
    client = TestClient(app)
    response = client.post(
        "/api/orchestrate",
        json={"profile": "mobile-android", "test_type": "mobile", "task": "add to cart checkout"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["error"] == "Safety policy violation"
    codes = {violation["code"] for violation in body["violations"]}
    assert {"cart", "checkout"}.issubset(codes)


def test_mock_profile_allows_checkout_order_tracking():
    client = TestClient(app)
    response = client.post(
        "/api/orchestrate",
        json={"profile": "mock", "test_type": "e2e", "task": "checkout order tracking"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body.get("error") != "Safety policy violation"
    assert body["profile"]["id"] == "mock"


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
