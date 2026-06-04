from __future__ import annotations

from fastapi.testclient import TestClient

from mock_api.server import app


def _auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/v2/user/login", json={"email": "test@test.com", "password": "Test123!"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_discovery_surfaces_match_yemeksepeti_public_tabs():
    client = TestClient(app)
    response = client.get("/v2/discovery/surfaces")
    assert response.status_code == 200
    labels = {surface["label"] for surface in response.json()["surfaces"]}
    assert {"Restoran", "Gel Al", "Marketler"} == labels


def test_address_suggestions_are_district_level_only():
    client = TestClient(app)
    response = client.get("/v2/addresses/suggestions", params={"query": "Kadıköy"})
    assert response.status_code == 200
    suggestions = response.json()["suggestions"]
    assert suggestions
    assert suggestions[0]["district"] == "Kadıköy"
    assert "phone" not in suggestions[0]
    assert "payment" not in suggestions[0]


def test_pickup_and_market_search_surfaces():
    client = TestClient(app)
    pickup = client.get("/v2/restaurants/search", params={"serviceType": "pickup", "district": "Kadıköy"})
    assert pickup.status_code == 200
    assert pickup.json()["total"] >= 1

    markets = client.get("/v2/markets/search", params={"query": "su", "district": "Kadıköy"})
    assert markets.status_code == 200
    assert markets.json()["total"] >= 1


def test_coupon_validation_uses_test_only_codes():
    client = TestClient(app)
    headers = _auth_headers(client)
    ok = client.post("/v2/coupons/validate", json={"code": "TEST10"}, headers=headers)
    assert ok.status_code == 200
    assert ok.json()["discount"] == 10.0

    invalid = client.post("/v2/coupons/validate", json={"code": "REALCARD"}, headers=headers)
    assert invalid.status_code == 404
