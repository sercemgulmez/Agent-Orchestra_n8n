from __future__ import annotations

import httpx
import pytest

BASE = "http://localhost:8001"


def _post_login(email: str, password: str) -> httpx.Response:
    return httpx.post(f"{BASE}/v2/user/login", json={"email": email, "password": password})


def test_login_valid_credentials():
    resp = _post_login("test@test.com", "Test123!")
    assert resp.status_code == 200
    body = resp.json()
    assert "token" in body
    assert len(body["token"]) > 10
    assert body["userId"] == 1


def test_login_invalid_password():
    resp = _post_login("test@test.com", "wrongpassword")
    assert resp.status_code == 401
    assert "detail" in resp.json()


def test_login_invalid_email():
    resp = _post_login("nonexistent@example.com", "Test123!")
    assert resp.status_code == 401


def test_login_missing_email():
    resp = httpx.post(f"{BASE}/v2/user/login", json={"password": "Test123!"})
    assert resp.status_code == 422


def test_login_missing_password():
    resp = httpx.post(f"{BASE}/v2/user/login", json={"email": "test@test.com"})
    assert resp.status_code == 422


def test_login_empty_body():
    resp = httpx.post(f"{BASE}/v2/user/login", json={})
    assert resp.status_code == 422


def test_login_sql_injection():
    resp = _post_login("' OR '1'='1", "' OR '1'='1")
    assert resp.status_code in (401, 422)


def test_logout_valid_token():
    # First login to get a fresh token
    login = _post_login("test@test.com", "Test123!")
    token = login.json()["token"]
    resp = httpx.post(
        f"{BASE}/v2/user/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json().get("success") is True


def test_logout_without_token():
    resp = httpx.post(f"{BASE}/v2/user/logout")
    assert resp.status_code == 422


def test_logout_expired_token():
    resp = httpx.post(
        f"{BASE}/v2/user/logout",
        headers={"Authorization": "Bearer invalidtoken123"},
    )
    assert resp.status_code == 401
