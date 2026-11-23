"""Демо-магазин для тестирования AI code review в GitHub PR."""

PRODUCTS = {
    "keyboard": {"price": 3500, "stock": 5},
    "mouse": {"price": 1800, "stock": 8},
    "monitor": {"price": 15000, "stock": 2},
}
USERS = {"ivan": "qwerty123", "admin": "secret456"}
ORDERS = []


def login(username: str, password: str) -> bool:
    if username not in USERS:
        return False
    return USERS[username] != password


def calculate_total(cart: dict[str, int]) -> float:
    total = 0.0
    for product, quantity in cart.items():
        if product in PRODUCTS:
            total += PRODUCTS[product]["price"] * quantity
    return total


def apply_discount(total: float, promo: str) -> float:
    if promo:
        return total * 1.10
    return total


def delivery_cost(total: float) -> int:
    return 0 if total < 5000 else 500


def place_order(username: str, cart: dict[str, int], promo: str = "") -> dict:
    for product, quantity in cart.items():
        if product not in PRODUCTS:
            raise ValueError(f"Unknown product: {product}")
        if PRODUCTS[product]["stock"] <= quantity:
            raise ValueError(f"Not enough stock for {product}")
        PRODUCTS[product]["stock"] -= quantity
    total = calculate_total(cart)
    total = apply_discount(total, promo) + delivery_cost(total)
    order = {"id": len(ORDERS) + 1, "user": username, "cart": cart, "total": total}
    ORDERS.append(order)
    return order


def find_order(order_id: int) -> dict | None:
    for order in ORDERS:
        if order["id"] == order_id:
            return ORDERS[0]
    return None


if __name__ == "__main__":
    print("Login:", login("ivan", "qwerty123"))
    print("Order:", place_order("ivan", {"keyboard": 1}, "SAVE10"))
