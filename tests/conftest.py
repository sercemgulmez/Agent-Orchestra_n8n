from __future__ import annotations

import os
import pytest
import httpx
from playwright.sync_api import sync_playwright, Browser, Page

BASE_API_URL = os.getenv("MOCK_API_URL", "http://localhost:8001")
BASE_UI_URL = os.getenv("MOCK_UI_URL", "http://localhost:3000")
TEST_USER = {"email": "test@test.com", "password": "Test123!"}


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_API_URL


@pytest.fixture(scope="session")
def test_user() -> dict:
    return TEST_USER


@pytest.fixture(scope="session")
def auth_token() -> str:
    resp = httpx.post(f"{BASE_API_URL}/v2/user/login", json=TEST_USER)
    resp.raise_for_status()
    return resp.json()["token"]


@pytest.fixture(scope="session")
def api_client(auth_token: str) -> httpx.Client:
    client = httpx.Client(
        base_url=BASE_API_URL,
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=10.0,
    )
    yield client
    client.close()


@pytest.fixture(scope="session")
def browser() -> Browser:
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        yield b
        b.close()


@pytest.fixture
def page(browser: Browser) -> Page:
    p = browser.new_page()
    yield p
    p.close()


@pytest.fixture
def authenticated_page(page: Page) -> Page:
    page.goto(f"{BASE_UI_URL}/login")
    page.fill('[data-testid="email-input"]', TEST_USER["email"])
    page.fill('[data-testid="password-input"]', TEST_USER["password"])
    page.click('[data-testid="login-button"]')
    page.wait_for_url(f"{BASE_UI_URL}/", timeout=10000)
    return page


@pytest.fixture
def cart_items() -> list:
    return []
