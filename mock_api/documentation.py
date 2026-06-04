YEMEKSEPETI_COMPLETE_DOCS = {
    "product": {
        "name": "Yemeksepeti web and app mirror",
        "public_surfaces": ["Giriş Yap", "Restoran", "Gel Al", "Marketler"],
        "safe_testing_policy": "No live ordering, payment, scraping, or personal accounts. Use mock/staging test accounts only.",
    },
    "test_profiles": [
        {
            "id": "mock",
            "target": "local mirror",
            "allows_side_effects": True,
            "description": "Full API, web, mobile, and E2E tests run against local mock services.",
        },
        {
            "id": "web-prod-smoke",
            "target": "https://www.yemeksepeti.com/",
            "allows_side_effects": False,
            "description": "Read-only smoke/navigation checks for public web surfaces only.",
        },
        {
            "id": "mobile-android",
            "target": "Appium Android emulator or real device",
            "allows_side_effects": False,
            "description": "Black-box Appium scenarios; app path and test credentials come from env.",
        },
        {
            "id": "mobile-ios",
            "target": "Appium iOS simulator or real device",
            "allows_side_effects": False,
            "description": "Black-box Appium scenarios; app path and test credentials come from env.",
        },
    ],
    "api": {
        "base_url": "http://localhost:8001",
        "endpoints": [
            {
                "method": "POST",
                "path": "/v2/user/login",
                "name": "User login",
                "request": {"email": "test@test.com", "password": "Test123!"},
                "responses": {"200": "token, userId, name", "401": "Invalid credentials"},
                "scenarios": ["valid login", "invalid password", "missing email"],
            },
            {
                "method": "GET",
                "path": "/v2/restaurants/search",
                "name": "Restaurant search",
                "query": {"query": "burger", "cuisine": "burger", "serviceType": "delivery", "page": 1, "limit": 20},
                "responses": {"200": "restaurants, total, page"},
                "scenarios": ["search all", "filter by cuisine", "delivery", "gel al", "empty results"],
            },
            {
                "method": "GET",
                "path": "/v2/markets/search",
                "name": "Market search",
                "query": {"query": "su", "category": "icecek"},
                "responses": {"200": "markets, total"},
                "scenarios": ["market tab loads", "product search", "empty market results"],
            },
            {
                "method": "GET",
                "path": "/v2/addresses/suggestions",
                "name": "Address suggestions",
                "query": {"query": "Kadıköy"},
                "responses": {"200": "suggestions"},
                "scenarios": ["location entry", "district suggestions", "no personal address persisted"],
            },
            {
                "method": "GET",
                "path": "/v2/restaurants/{id}/menu",
                "name": "Restaurant menu",
                "path_params": {"id": 1},
                "responses": {"200": "restaurantId, categories", "404": "Restaurant not found"},
                "scenarios": ["full menu", "invalid restaurant id"],
            },
            {
                "method": "POST",
                "path": "/v2/cart/add",
                "name": "Add item to cart",
                "request": {"itemId": 101, "quantity": 1, "restaurantId": 1},
                "responses": {"200": "cart", "400": "Different restaurant", "404": "Item not found"},
                "scenarios": ["add new item", "invalid quantity", "different restaurant"],
            },
            {
                "method": "POST",
                "path": "/v2/orders/create",
                "name": "Create order",
                "request": {
                    "restaurantId": 1,
                    "items": [{"itemId": 101, "quantity": 1}],
                    "deliveryAddress": "Istanbul",
                    "paymentMethod": "card",
                },
                "responses": {"201": "orderId, status, estimatedTime", "400": "Invalid order"},
                "scenarios": ["valid test order", "empty cart", "coupon applied", "invalid payment method"],
            },
            {
                "method": "POST",
                "path": "/v2/coupons/validate",
                "name": "Validate coupon",
                "request": {"code": "TEST10"},
                "responses": {"200": "discount, message", "404": "Invalid coupon"},
                "scenarios": ["valid coupon", "invalid coupon", "coupon without cart"],
            },
            {
                "method": "GET",
                "path": "/v2/orders/{id}/track",
                "name": "Track order",
                "path_params": {"id": "order-id"},
                "responses": {"200": "status, statusIndex, estimatedMinutes", "404": "Order not found"},
                "scenarios": ["track in progress", "track delivered", "missing order"],
            },
        ],
    },
    "ui": {
        "pages": [
            {"url": "/login", "name": "Login", "scenarios": ["valid login", "invalid login"]},
            {"url": "/", "name": "Home", "scenarios": ["restaurant list", "search", "gel al tab", "marketler tab", "location entry"]},
            {"url": "/restaurant/{id}", "name": "Restaurant detail", "scenarios": ["menu", "add cart"]},
            {"url": "/cart", "name": "Cart", "scenarios": ["quantity update", "remove item"]},
            {"url": "/checkout", "name": "Checkout", "scenarios": ["address", "payment", "submit order"]},
        ],
    },
    "mobile": {
        "framework": "Appium",
        "platforms": ["android", "ios"],
        "scenarios": [
            "open app and verify login entry",
            "set delivery location",
            "switch between restaurant, gel al, and market surfaces",
            "search and open listing details",
            "add item to cart in mock/staging only",
        ],
    },
    "e2e_journeys": [
        {
            "name": "Tam sipariş akışı",
            "steps": ["login", "set location", "search", "open restaurant", "add cart", "coupon", "checkout", "track order"],
        },
        {
            "name": "Sepet yönetimi",
            "steps": ["login", "open restaurant", "add item", "update quantity", "remove item"],
        },
        {
            "name": "Marketler akışı",
            "steps": ["login", "set location", "open marketler", "search product", "add product", "checkout"],
        },
        {
            "name": "Gel al akışı",
            "steps": ["login", "open gel al", "filter pickup restaurants", "open restaurant", "add item"],
        },
    ],
}


API_DOCS = {
    "version": "2.0.0",
    "baseUrl": YEMEKSEPETI_COMPLETE_DOCS["api"]["base_url"],
    "description": "Yemeksepeti-style mock API for test automation",
    "endpoints": {
        endpoint["path"]: endpoint for endpoint in YEMEKSEPETI_COMPLETE_DOCS["api"]["endpoints"]
    },
    "uiPages": {
        page["url"]: page for page in YEMEKSEPETI_COMPLETE_DOCS["ui"]["pages"]
    },
    "e2eJourneys": YEMEKSEPETI_COMPLETE_DOCS["e2e_journeys"],
}
