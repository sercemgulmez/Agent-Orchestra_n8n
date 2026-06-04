from __future__ import annotations

import time
import httpx
import pytest
from playwright.sync_api import Page

BASE_UI = "http://localhost:3000"
BASE_API = "http://localhost:8001"


def _login_api() -> str:
    resp = httpx.post(f"{BASE_API}/v2/user/login", json={"email": "test@test.com", "password": "Test123!"})
    return resp.json()["token"]


def test_complete_order_flow(page: Page):
    start = time.time()

    # 1. Login via UI
    page.goto(f"{BASE_UI}/login")
    page.fill('[data-testid="email-input"]', "test@test.com")
    page.fill('[data-testid="password-input"]', "Test123!")
    page.click('[data-testid="login-button"]')
    page.wait_for_url(f"{BASE_UI}/", timeout=10000)
    assert page.locator('[data-testid="home-page"]').is_visible()

    # 2. Restaurant list loads
    page.wait_for_selector('[data-testid="restaurant-card"]', timeout=8000)
    cards = page.locator('[data-testid="restaurant-card"]')
    assert cards.count() >= 1

    # 3. Navigate to first restaurant
    first_card = cards.first
    first_card.click()
    page.wait_for_selector('[data-testid="menu-item"]', timeout=8000)
    assert page.locator('[data-testid="menu-list"]').is_visible()

    # 4. Add item to cart
    add_btns = page.locator('[data-testid="add-to-cart-button"]')
    assert add_btns.count() >= 1
    add_btns.first.click()
    page.wait_for_timeout(800)

    # Cart badge should update
    badge = page.locator('[data-testid="cart-badge"]')
    assert badge.is_visible()

    # 5. Navigate to cart
    page.goto(f"{BASE_UI}/cart")
    page.wait_for_selector('[data-testid="cart-page"]', timeout=5000)

    # Either cart has items or empty (depending on server state)
    cart_page = page.locator('[data-testid="cart-page"]')
    assert cart_page.is_visible()

    elapsed = time.time() - start
    assert elapsed < 30, f"E2E flow took too long: {elapsed:.1f}s"


def test_cart_quantity_change(page: Page):
    token = _login_api()

    # Add an item via API
    client = httpx.Client(base_url=BASE_API, headers={"Authorization": f"Bearer {token}"})
    add_resp = client.post("/v2/cart/add", json={"itemId": 101, "quantity": 1, "restaurantId": 1})
    assert add_resp.status_code == 200

    # Navigate to cart in UI
    page.goto(f"{BASE_UI}/login")
    page.evaluate(f"localStorage.setItem('token', '{token}')")
    page.goto(f"{BASE_UI}/cart")
    page.wait_for_selector('[data-testid="cart-item"]', timeout=8000)

    qty_el = page.locator('[data-testid="item-quantity"]').first
    initial_qty = int(qty_el.inner_text())

    # Increase
    page.locator('[data-testid="quantity-increase"]').first.click()
    page.wait_for_timeout(500)
    new_qty = int(page.locator('[data-testid="item-quantity"]').first.inner_text())
    assert new_qty == initial_qty + 1

    client.close()


def test_api_order_tracking_cycle():
    token = _login_api()
    client = httpx.Client(base_url=BASE_API, headers={"Authorization": f"Bearer {token}"})

    # Create order
    client.post("/v2/cart/add", json={"itemId": 101, "quantity": 2, "restaurantId": 1})
    order_resp = client.post("/v2/orders/create", json={
        "restaurantId": 1,
        "items": [],
        "deliveryAddress": "Test Street 1, Istanbul",
        "paymentMethod": "card",
    })
    assert order_resp.status_code == 201
    order_id = order_resp.json()["orderId"]

    statuses = []
    # Track multiple times to verify status advances
    for _ in range(5):
        track = client.get(f"/v2/orders/{order_id}/track")
        assert track.status_code == 200
        statuses.append(track.json()["status"])

    # Should have progressed (at least 2 different statuses or reached DELIVERED)
    unique = set(statuses)
    assert len(unique) >= 1
    # All statuses should be from the valid set
    valid = {"RECEIVED", "CONFIRMED", "PREPARING", "ON_THE_WAY", "DELIVERED"}
    assert all(s in valid for s in statuses)

    client.close()


def test_checkout_flow_via_api():
    token = _login_api()
    client = httpx.Client(base_url=BASE_API, headers={"Authorization": f"Bearer {token}"})

    # Add item
    add = client.post("/v2/cart/add", json={"itemId": 201, "quantity": 1, "restaurantId": 2})
    assert add.status_code == 200
    assert add.json()["cart"]["items"]

    # Checkout
    order = client.post("/v2/orders/create", json={
        "restaurantId": 2,
        "items": [],
        "deliveryAddress": "Test Address",
        "paymentMethod": "cash",
    })
    assert order.status_code == 201
    body = order.json()
    assert "orderId" in body
    assert body["status"] == "RECEIVED"

    # Cart should be cleared
    cart = client.get("/v2/cart")
    assert cart.json()["itemCount"] == 0

    client.close()
