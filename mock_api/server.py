from __future__ import annotations

import secrets
import uuid
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

app = FastAPI(title="YemekTest Mock API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory data store
# ---------------------------------------------------------------------------

USERS: List[Dict] = [
    {"id": 1, "email": "test@test.com",  "password": "Test123!", "name": "Test Kullanıcı"},
    {"id": 2, "email": "admin@test.com", "password": "Admin123!", "name": "Admin"},
    {"id": 3, "email": "zeynep@test.com","password": "Zeynep99!", "name": "Zeynep Kaya"},
]

RESTAURANTS: List[Dict] = [
    {
        "id": 1, "name": "Burger Palace", "cuisine": "burger",
        "rating": 4.5, "deliveryTime": 25, "minimumOrder": 50.0,
        "serviceTypes": ["delivery", "pickup"],
        "districts": ["Kadıköy", "Beşiktaş", "Şişli"],
        "imageUrl": "https://via.placeholder.com/300x200?text=Burger+Palace",
        "menu": [
            {"categoryId": 1, "categoryName": "Burgerler", "items": [
                {"id": 101, "name": "Classic Burger",    "price": 89.90, "description": "Klasik dana burger"},
                {"id": 102, "name": "Cheese Burger",     "price": 99.90, "description": "Kaşarlı burger"},
                {"id": 103, "name": "Double Smash",      "price": 129.90,"description": "Çift patty smash burger"},
            ]},
            {"categoryId": 2, "categoryName": "Yanlar", "items": [
                {"id": 104, "name": "Patates Kızartması","price": 39.90, "description": "Çıtır patates"},
                {"id": 105, "name": "Onion Rings",       "price": 44.90, "description": "Soğan halkası"},
            ]},
            {"categoryId": 3, "categoryName": "İçecekler", "items": [
                {"id": 106, "name": "Cola",  "price": 24.90, "description": "330ml kutu"},
            ]},
        ],
    },
    {
        "id": 2, "name": "Pizza House", "cuisine": "pizza",
        "rating": 4.2, "deliveryTime": 35, "minimumOrder": 80.0,
        "serviceTypes": ["delivery", "pickup"],
        "districts": ["Kadıköy", "Ataşehir"],
        "imageUrl": "https://via.placeholder.com/300x200?text=Pizza+House",
        "menu": [
            {"categoryId": 1, "categoryName": "Pizzalar", "items": [
                {"id": 201, "name": "Margherita",   "price": 119.90, "description": "Domates sos, mozzarella"},
                {"id": 202, "name": "Pepperoni",    "price": 139.90, "description": "Sucuklu pizza"},
                {"id": 203, "name": "Karışık",      "price": 149.90, "description": "Karışık malzemeli"},
                {"id": 204, "name": "Vejeteryan",   "price": 129.90, "description": "Sebzeli pizza"},
            ]},
            {"categoryId": 2, "categoryName": "Yan Ürünler", "items": [
                {"id": 205, "name": "Garlic Bread",  "price": 49.90, "description": "Sarımsaklı ekmek"},
                {"id": 206, "name": "Caesar Salad",  "price": 59.90, "description": "Sezar salata"},
            ]},
        ],
    },
    {
        "id": 3, "name": "Sushi Bar", "cuisine": "sushi",
        "rating": 4.8, "deliveryTime": 45, "minimumOrder": 150.0,
        "serviceTypes": ["delivery"],
        "districts": ["Beşiktaş", "Sarıyer"],
        "imageUrl": "https://via.placeholder.com/300x200?text=Sushi+Bar",
        "menu": [
            {"categoryId": 1, "categoryName": "Maki", "items": [
                {"id": 301, "name": "Salmon Maki (8pc)",  "price": 149.90, "description": "Somon maki"},
                {"id": 302, "name": "Tuna Maki (8pc)",    "price": 159.90, "description": "Ton balığı maki"},
                {"id": 303, "name": "Rainbow Roll (8pc)", "price": 179.90, "description": "Rainbow rulo"},
            ]},
            {"categoryId": 2, "categoryName": "Nigiri", "items": [
                {"id": 304, "name": "Salmon Nigiri (2pc)","price": 89.90, "description": "Somon nigiri"},
                {"id": 305, "name": "Tuna Nigiri (2pc)",  "price": 99.90, "description": "Ton nigiri"},
            ]},
        ],
    },
    {
        "id": 4, "name": "Köfte Evi", "cuisine": "turkish",
        "rating": 4.6, "deliveryTime": 30, "minimumOrder": 60.0,
        "serviceTypes": ["delivery", "pickup"],
        "districts": ["Üsküdar", "Kadıköy"],
        "imageUrl": "https://via.placeholder.com/300x200?text=Kofte+Evi",
        "menu": [
            {"categoryId": 1, "categoryName": "Köfteler", "items": [
                {"id": 401, "name": "Izgara Köfte",  "price": 109.90, "description": "Izgara dana köfte"},
                {"id": 402, "name": "İzmir Köfte",   "price": 119.90, "description": "Domates soslu fırın köfte"},
                {"id": 403, "name": "Kasap Köfte",   "price": 129.90, "description": "El yapımı kasap köfte"},
            ]},
            {"categoryId": 2, "categoryName": "Mezeler", "items": [
                {"id": 404, "name": "Cacık",  "price": 34.90, "description": "Yoğurtlu cacık"},
                {"id": 405, "name": "Ezme",   "price": 34.90, "description": "Acılı ezme"},
            ]},
        ],
    },
    {
        "id": 5, "name": "Döner King", "cuisine": "doner",
        "rating": 4.3, "deliveryTime": 20, "minimumOrder": 45.0,
        "serviceTypes": ["delivery", "pickup"],
        "districts": ["Şişli", "Kağıthane"],
        "imageUrl": "https://via.placeholder.com/300x200?text=Doner+King",
        "menu": [
            {"categoryId": 1, "categoryName": "Dönerler", "items": [
                {"id": 501, "name": "Tavuk Döner",  "price": 79.90, "description": "Tavuk döner dürüm"},
                {"id": 502, "name": "Et Döner",     "price": 99.90, "description": "Et döner dürüm"},
                {"id": 503, "name": "Karışık Döner","price": 109.90,"description": "Karışık döner porsiyon"},
            ]},
            {"categoryId": 2, "categoryName": "Ekstralar", "items": [
                {"id": 504, "name": "Acı Sos",   "price": 9.90,  "description": "Ev yapımı acı sos"},
                {"id": 505, "name": "Sarımsaklı Yoğurt", "price": 14.90, "description": "Sarımsaklı yoğurt"},
            ]},
        ],
    },
]

MARKETS: List[Dict] = [
    {
        "id": 1001,
        "name": "YS Market Kadıköy",
        "rating": 4.7,
        "deliveryTime": 18,
        "minimumOrder": 100.0,
        "category": "market",
        "districts": ["Kadıköy", "Ataşehir"],
        "products": [
            {"id": 9001, "name": "Su 1.5L", "price": 12.90, "description": "Şişe su"},
            {"id": 9002, "name": "Süt 1L", "price": 34.90, "description": "Günlük süt"},
            {"id": 9003, "name": "Ekmek", "price": 10.00, "description": "Taze ekmek"},
        ],
    },
    {
        "id": 1002,
        "name": "YS Hızlı Market Beşiktaş",
        "rating": 4.5,
        "deliveryTime": 22,
        "minimumOrder": 120.0,
        "category": "market",
        "districts": ["Beşiktaş", "Şişli"],
        "products": [
            {"id": 9011, "name": "Kahve", "price": 89.90, "description": "Filtre kahve"},
            {"id": 9012, "name": "Makarna", "price": 29.90, "description": "500g makarna"},
        ],
    },
]

ADDRESS_SUGGESTIONS: List[Dict] = [
    {"id": "addr-kadikoy", "label": "Kadıköy, İstanbul", "district": "Kadıköy", "city": "İstanbul"},
    {"id": "addr-besiktas", "label": "Beşiktaş, İstanbul", "district": "Beşiktaş", "city": "İstanbul"},
    {"id": "addr-sisli", "label": "Şişli, İstanbul", "district": "Şişli", "city": "İstanbul"},
    {"id": "addr-atasehir", "label": "Ataşehir, İstanbul", "district": "Ataşehir", "city": "İstanbul"},
]

COUPONS = {
    "TEST10": {"code": "TEST10", "discount": 10.0, "message": "Test indirimi uygulandı."},
    "YSAPP": {"code": "YSAPP", "discount": 15.0, "message": "Mobil app test kuponu uygulandı."},
}

# Runtime state
ACTIVE_TOKENS: Dict[str, int] = {}  # token -> user_id
CARTS: Dict[int, List[Dict]] = {}   # user_id -> list of cart items
ORDERS: Dict[str, Dict] = {}        # order_id -> order

ORDER_STATUSES = ["RECEIVED", "CONFIRMED", "PREPARING", "ON_THE_WAY", "DELIVERED"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_user_by_email(email: str) -> Optional[Dict]:
    return next((u for u in USERS if u["email"] == email), None)


def _find_restaurant(rid: int) -> Optional[Dict]:
    return next((r for r in RESTAURANTS if r["id"] == rid), None)


def _find_menu_item(item_id: int) -> Optional[tuple[Dict, Dict]]:
    for r in RESTAURANTS:
        for cat in r["menu"]:
            for item in cat["items"]:
                if item["id"] == item_id:
                    return item, r
    return None, None


def _find_market_product(item_id: int) -> Optional[tuple[Dict, Dict]]:
    for market in MARKETS:
        for item in market["products"]:
            if item["id"] == item_id:
                return item, market
    return None, None


def _cart_total(cart_items: List[Dict]) -> float:
    return round(sum(i["price"] * i["quantity"] for i in cart_items), 2)


async def get_current_user(authorization: str = Header(...)) -> Dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")
    token = authorization[7:]
    user_id = ACTIVE_TOKENS.get(token)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = next((u for u in USERS if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


# ---------------------------------------------------------------------------
# Auth models
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

@app.post("/v2/user/login", status_code=200)
async def login(req: LoginRequest):
    user = _find_user_by_email(req.email)
    if not user or user["password"] != req.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = secrets.token_hex(32)
    ACTIVE_TOKENS[token] = user["id"]
    return {"token": token, "userId": user["id"], "name": user["name"]}


@app.post("/v2/user/logout", status_code=200)
async def logout(current_user: Dict = Depends(get_current_user), authorization: str = Header(...)):
    token = authorization[7:]
    ACTIVE_TOKENS.pop(token, None)
    return {"success": True}


@app.post("/v2/user/register", status_code=201)
async def register(req: RegisterRequest):
    if _find_user_by_email(req.email):
        raise HTTPException(status_code=409, detail="Email already registered")
    if len(req.password) < 6:
        raise HTTPException(status_code=422, detail="Password must be at least 6 characters")
    new_id = max(u["id"] for u in USERS) + 1
    new_user = {"id": new_id, "email": req.email, "password": req.password, "name": req.name}
    USERS.append(new_user)
    token = secrets.token_hex(32)
    ACTIVE_TOKENS[token] = new_id
    return {"userId": new_id, "token": token}


# ---------------------------------------------------------------------------
# Restaurant endpoints
# ---------------------------------------------------------------------------

@app.get("/v2/restaurants/search")
async def search_restaurants(
    query: Optional[str] = None,
    cuisine: Optional[str] = None,
    serviceType: Optional[str] = None,
    district: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
):
    results = RESTAURANTS[:]
    if query:
        q = query.lower()
        results = [r for r in results if q in r["name"].lower() or q in r["cuisine"].lower()]
    if cuisine:
        results = [r for r in results if r["cuisine"] == cuisine.lower()]
    if serviceType:
        results = [r for r in results if serviceType in r.get("serviceTypes", [])]
    if district:
        results = [r for r in results if district in r.get("districts", [])]
    start = (page - 1) * limit
    paged = results[start: start + limit]
    clean = [{k: v for k, v in r.items() if k != "menu"} for r in paged]
    return {"restaurants": clean, "total": len(results), "page": page}


@app.get("/v2/discovery/surfaces")
async def discovery_surfaces():
    return {
        "surfaces": [
            {"id": "restaurants", "label": "Restoran", "serviceType": "delivery"},
            {"id": "pickup", "label": "Gel Al", "serviceType": "pickup"},
            {"id": "markets", "label": "Marketler", "serviceType": "market"},
        ],
        "safeTestingPolicy": "Mock/staging only for login, cart, checkout, and mobile flows.",
    }


@app.get("/v2/addresses/suggestions")
async def address_suggestions(query: Optional[str] = None):
    if not query:
        return {"suggestions": ADDRESS_SUGGESTIONS}
    q = query.lower()
    return {"suggestions": [a for a in ADDRESS_SUGGESTIONS if q in a["label"].lower()]}


@app.get("/v2/markets/search")
async def search_markets(query: Optional[str] = None, district: Optional[str] = None):
    results = MARKETS[:]
    if district:
        results = [m for m in results if district in m.get("districts", [])]
    if query:
        q = query.lower()
        results = [
            m for m in results
            if q in m["name"].lower() or any(q in p["name"].lower() for p in m["products"])
        ]
    clean = [{k: v for k, v in m.items() if k != "products"} for m in results]
    return {"markets": clean, "total": len(clean)}


@app.get("/v2/markets/{market_id}/products")
async def market_products(market_id: int):
    market = next((m for m in MARKETS if m["id"] == market_id), None)
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    return {"marketId": market_id, "marketName": market["name"], "products": market["products"]}


@app.get("/v2/restaurants/{restaurant_id}")
async def get_restaurant(restaurant_id: int):
    r = _find_restaurant(restaurant_id)
    if not r:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return {k: v for k, v in r.items() if k != "menu"}


@app.get("/v2/restaurants/{restaurant_id}/menu")
async def get_menu(restaurant_id: int):
    r = _find_restaurant(restaurant_id)
    if not r:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return {"restaurantId": restaurant_id, "restaurantName": r["name"], "categories": r["menu"]}


# ---------------------------------------------------------------------------
# Cart endpoints
# ---------------------------------------------------------------------------

class CartAddRequest(BaseModel):
    itemId: int
    quantity: int
    restaurantId: int


class CartUpdateRequest(BaseModel):
    itemId: int
    quantity: int


class CartRemoveRequest(BaseModel):
    itemId: int


@app.get("/v2/cart")
async def get_cart(current_user: Dict = Depends(get_current_user)):
    items = CARTS.get(current_user["id"], [])
    return {"items": items, "total": _cart_total(items), "itemCount": len(items)}


@app.post("/v2/cart/add")
async def add_to_cart(req: CartAddRequest, current_user: Dict = Depends(get_current_user)):
    uid = current_user["id"]
    item_data, restaurant = _find_menu_item(req.itemId)
    source_type = "restaurant"
    if not item_data:
        item_data, restaurant = _find_market_product(req.itemId)
        source_type = "market"
    if not item_data:
        raise HTTPException(status_code=404, detail="Item not found")
    if source_type == "restaurant" and restaurant["id"] != req.restaurantId:
        raise HTTPException(status_code=400, detail="Item does not belong to specified restaurant")

    cart = CARTS.setdefault(uid, [])
    existing = next((c for c in cart if c["itemId"] == req.itemId), None)
    if existing:
        existing["quantity"] += req.quantity
    else:
        cart.append({
            "itemId": req.itemId,
            "name": item_data["name"],
            "price": item_data["price"],
            "quantity": req.quantity,
            "restaurantId": req.restaurantId,
            "sourceType": source_type,
        })
    return {"cart": {"items": cart, "total": _cart_total(cart)}}


class CouponRequest(BaseModel):
    code: str


@app.post("/v2/coupons/validate")
async def validate_coupon(req: CouponRequest, current_user: Dict = Depends(get_current_user)):
    coupon = COUPONS.get(req.code.upper())
    if not coupon:
        raise HTTPException(status_code=404, detail="Invalid coupon")
    cart_total = _cart_total(CARTS.get(current_user["id"], []))
    return {
        **coupon,
        "cartTotal": cart_total,
        "discountedTotal": max(0, round(cart_total - coupon["discount"], 2)),
    }


@app.put("/v2/cart/update")
async def update_cart(req: CartUpdateRequest, current_user: Dict = Depends(get_current_user)):
    uid = current_user["id"]
    cart = CARTS.get(uid, [])
    item = next((c for c in cart if c["itemId"] == req.itemId), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not in cart")
    if req.quantity <= 0:
        CARTS[uid] = [c for c in cart if c["itemId"] != req.itemId]
    else:
        item["quantity"] = req.quantity
    updated = CARTS.get(uid, [])
    return {"cart": {"items": updated, "total": _cart_total(updated)}}


@app.delete("/v2/cart/remove")
async def remove_from_cart(req: CartRemoveRequest, current_user: Dict = Depends(get_current_user)):
    uid = current_user["id"]
    cart = CARTS.get(uid, [])
    if not any(c["itemId"] == req.itemId for c in cart):
        raise HTTPException(status_code=404, detail="Item not in cart")
    CARTS[uid] = [c for c in cart if c["itemId"] != req.itemId]
    updated = CARTS[uid]
    return {"cart": {"items": updated, "total": _cart_total(updated)}}


# ---------------------------------------------------------------------------
# Order endpoints
# ---------------------------------------------------------------------------

class CreateOrderRequest(BaseModel):
    restaurantId: int
    items: List[Dict[str, Any]]
    deliveryAddress: str
    paymentMethod: str


@app.post("/v2/orders/create", status_code=201)
async def create_order(req: CreateOrderRequest, current_user: Dict = Depends(get_current_user)):
    uid = current_user["id"]
    if req.paymentMethod not in ("cash", "card", "online"):
        raise HTTPException(status_code=400, detail="Invalid payment method")
    items = req.items or CARTS.get(uid, [])
    if not items:
        raise HTTPException(status_code=400, detail="Empty cart")
    total = sum(i.get("price", 0) * i.get("quantity", 1) for i in items)
    restaurant = _find_restaurant(req.restaurantId)
    if restaurant and total < restaurant["minimumOrder"]:
        raise HTTPException(status_code=400, detail=f"Below minimum order: {restaurant['minimumOrder']}")
    order_id = str(uuid.uuid4())[:8].upper()
    ORDERS[order_id] = {
        "orderId": order_id,
        "userId": uid,
        "restaurantId": req.restaurantId,
        "items": items,
        "total": round(total, 2),
        "deliveryAddress": req.deliveryAddress,
        "paymentMethod": req.paymentMethod,
        "statusIndex": 0,
        "status": ORDER_STATUSES[0],
    }
    CARTS[uid] = []
    return {"orderId": order_id, "status": ORDER_STATUSES[0], "estimatedTime": 35}


@app.get("/v2/orders/history")
async def order_history(current_user: Dict = Depends(get_current_user)):
    uid = current_user["id"]
    user_orders = [o for o in ORDERS.values() if o["userId"] == uid]
    return {"orders": user_orders, "total": len(user_orders)}


@app.get("/v2/orders/{order_id}")
async def get_order(order_id: str, current_user: Dict = Depends(get_current_user)):
    order = ORDERS.get(order_id.upper())
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.get("/v2/orders/{order_id}/track")
async def track_order(order_id: str, current_user: Dict = Depends(get_current_user)):
    order = ORDERS.get(order_id.upper())
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    idx = order["statusIndex"]
    if idx < len(ORDER_STATUSES) - 1:
        order["statusIndex"] = idx + 1
        order["status"] = ORDER_STATUSES[idx + 1]
    remaining = max(0, (len(ORDER_STATUSES) - 1 - order["statusIndex"]) * 7)
    return {
        "orderId": order_id,
        "status": order["status"],
        "statusIndex": order["statusIndex"],
        "estimatedMinutes": remaining,
    }


# ---------------------------------------------------------------------------
# Docs endpoint
# ---------------------------------------------------------------------------

@app.get("/docs/api")
async def api_docs():
    from mock_api.documentation import API_DOCS
    return API_DOCS


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mock-api"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
