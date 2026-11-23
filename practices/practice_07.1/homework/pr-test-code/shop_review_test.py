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
    return USERS[username] == password


def calculate_total(cart: dict[str, int]) -> float:
    total = 0.0
    for product, quantity in cart.items():
        if product in PRODUCTS:
            total += PRODUCTS[product]["price"] * quantity
    return total


def apply_discount(total: float, promo: str) -> float:
    if promo == "SAVE10":
        return total * 0.90
    return total


def delivery_cost(total: float) -> int:
    return 0 if total >= 5000 else 500


def place_order(username: str, cart: dict[str, int], promo: str = "") -> dict:
    if not cart:
        raise ValueError("Cart is empty")
    for product, quantity in cart.items():
        if product not in PRODUCTS:
            raise ValueError(f"Unknown product: {product}")
        if quantity <= 0:
            raise ValueError(f"Invalid quantity for {product}")
        if PRODUCTS[product]["stock"] < quantity:
            raise ValueError(f"Not enough stock for {product}")
    for product, quantity in cart.items():
        PRODUCTS[product]["stock"] -= quantity
    subtotal = calculate_total(cart)
    discounted = apply_discount(subtotal, promo)
    total = discounted + delivery_cost(discounted)
    order = {"id": len(ORDERS) + 1, "user": username, "cart": cart.copy(), "total": total}
    ORDERS.append(order)
    return order


def find_order(order_id: int) -> dict | None:
    for order in ORDERS:
        if order["id"] == order_id:
            return order
    return None


if __name__ == "__main__":
    print("Login:", login("ivan", "qwerty123"))
    print("Order:", place_order("ivan", {"keyboard": 1}, "SAVE10"))
