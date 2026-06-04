from __future__ import annotations

from playwright.sync_api import Page

BASE_UI = "http://localhost:3000"


def _login(page: Page) -> None:
    page.goto(f"{BASE_UI}/login")
    page.fill('[data-testid="email-input"]', "test@test.com")
    page.fill('[data-testid="password-input"]', "Test123!")
    page.click('[data-testid="login-button"]')
    page.wait_for_url(f"{BASE_UI}/", timeout=10000)


def test_home_shows_yemeksepeti_mirror_surfaces(page: Page):
    _login(page)
    assert page.locator('[data-testid="safe-testing-banner"]').is_visible()
    assert page.locator('[data-testid="service-tabs"]').is_visible()
    assert page.locator('[data-testid="service-tab-restaurants"]').is_visible()
    assert page.locator('[data-testid="service-tab-pickup"]').is_visible()
    assert page.locator('[data-testid="service-tab-markets"]').is_visible()


def test_location_pickup_and_market_tabs(page: Page):
    _login(page)
    page.fill('[data-testid="location-input"]', "Kadıköy")
    page.click('[data-testid="location-search-button"]')
    page.wait_for_selector('[data-testid="selected-district"]')
    assert "Kadıköy" in page.locator('[data-testid="selected-district"]').inner_text()

    page.click('[data-testid="service-tab-pickup"]')
    page.wait_for_selector('[data-testid="restaurant-card"]')
    assert page.locator('[data-testid="service-type-label"]').first.is_visible()

    page.click('[data-testid="service-tab-markets"]')
    page.wait_for_selector('[data-testid="market-card"]')
    assert page.locator('[data-testid="market-list"]').is_visible()
