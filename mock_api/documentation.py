YEMEKSEPETI_COMPLETE_DOCS = {
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
                "query": {"query": "burger", "cuisine": "burger", "page": 1, "limit": 20},
                "responses": {"200": "restaurants, total, page"},
                "scenarios": ["search all", "filter by cuisine", "empty results"],
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
                "scenarios": ["valid order", "empty cart", "invalid payment method"],
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
            {"url": "/", "name": "Home", "scenarios": ["restaurant list", "search"]},
            {"url": "/restaurant/{id}", "name": "Restaurant detail", "scenarios": ["menu", "add cart"]},
            {"url": "/cart", "name": "Cart", "scenarios": ["quantity update", "remove item"]},
            {"url": "/checkout", "name": "Checkout", "scenarios": ["address", "payment", "submit order"]},
        ],
    },
    "e2e_journeys": [
        {
            "name": "Tam sipariş akışı",
            "steps": ["login", "search", "open restaurant", "add cart", "checkout", "track order"],
        },
        {
            "name": "Sepet yönetimi",
            "steps": ["login", "open restaurant", "add item", "update quantity", "remove item"],
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
