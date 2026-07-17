"""
Seed script — builds store.db, a small fictional e-commerce SQLite database
used by sql_agent.py.

Creates 4 tables with real foreign-key relationships:
    customers, products, orders, order_items

Data is randomized but deterministic (fixed random seed), so re-running
this script always produces the same customers/products and the same
*pattern* of orders — only the absolute calendar dates shift, since
order dates are generated relative to "now" (the last ~13 months).

Usage:
    python seed_database.py
"""

import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "store.db"
RANDOM_SEED = 42

# =============================================================
# Reference data
# =============================================================
ARABIC_FIRST_NAMES = [
    "Mohammed", "Ahmad", "Ali", "Omar", "Yousef", "Khaled", "Yasser", "Sami",
    "Majed", "Ibrahim", "Layla", "Fatima", "Sara", "Nour", "Heba", "Rana",
    "Dima", "Lina", "Yasmin", "Reem", "Hala", "Tariq", "Ziad", "Nadia",
]
ARABIC_LAST_NAMES = [
    "Al-Husseini", "Al-Nabulsi", "Al-Khalili", "Al-Omari", "Diab", "Hamdan",
    "Odeh", "Shaheen", "Qasem", "Darwish", "Al-Ahmad", "Saleh", "Mustafa",
    "Zeidan", "Al-Barghouti",
]
INTL_FIRST_NAMES = [
    "John", "Emma", "Liam", "Olivia", "Noah", "Sophia", "Lucas", "Mia",
    "Ethan", "Ava", "James", "Grace", "Daniel", "Chloe",
]
INTL_LAST_NAMES = [
    "Smith", "Johnson", "Brown", "Davis", "Wilson", "Miller", "Garcia",
    "Rodriguez", "Martinez", "Anderson", "Clark", "Lewis", "Walker", "Hall",
]

# (city, country)
CITIES = [
    ("Nablus", "Palestine"), ("Ramallah", "Palestine"), ("Hebron", "Palestine"),
    ("Jerusalem", "Palestine"), ("Gaza", "Palestine"), ("Bethlehem", "Palestine"),
    ("Jenin", "Palestine"), ("Tulkarm", "Palestine"), ("Qalqilya", "Palestine"),
    ("Jericho", "Palestine"),
    ("Dubai", "UAE"), ("Amman", "Jordan"), ("Cairo", "Egypt"),
    ("Istanbul", "Turkey"), ("London", "UK"), ("Berlin", "Germany"),
    ("Toronto", "Canada"), ("New York", "USA"), ("Doha", "Qatar"),
    ("Riyadh", "Saudi Arabia"),
]

# (name, category, price)
PRODUCTS = [
    ("Wireless Earbuds Pro", "Electronics", 59.99),
    ("4K Action Camera", "Electronics", 129.99),
    ("Smart Fitness Watch", "Electronics", 89.99),
    ("Portable Bluetooth Speaker", "Electronics", 39.99),
    ("USB-C Fast Charger 65W", "Electronics", 24.99),
    ("Stainless Steel Cookware Set", "Home & Kitchen", 149.99),
    ("Electric Kettle 1.7L", "Home & Kitchen", 29.99),
    ("Robot Vacuum Cleaner", "Home & Kitchen", 199.99),
    ("Non-Stick Frying Pan", "Home & Kitchen", 22.99),
    ("Ceramic Coffee Mug Set", "Home & Kitchen", 19.99),
    ("Leather Crossbody Bag", "Fashion", 69.99),
    ("Classic Denim Jacket", "Fashion", 54.99),
    ("Running Shoes", "Fashion", 79.99),
    ("Wool Winter Scarf", "Fashion", 17.99),
    ("Sunglasses UV400", "Fashion", 34.99),
    ("Arabic Calligraphy Notebook", "Books & Stationery", 9.99),
    ("Bestseller Novel Bundle", "Books & Stationery", 27.99),
    ("Premium Fountain Pen", "Books & Stationery", 14.99),
    ("Desk Planner 2025", "Books & Stationery", 12.99),
    ("Kids Coloring Book Set", "Books & Stationery", 8.99),
    ("Yoga Mat Non-Slip", "Sports & Outdoors", 21.99),
    ("Adjustable Dumbbell Set", "Sports & Outdoors", 119.99),
    ("Camping Tent 4-Person", "Sports & Outdoors", 89.99),
    ("Insulated Water Bottle", "Sports & Outdoors", 16.99),
    ("Resistance Bands Set", "Sports & Outdoors", 13.99),
    ("Vitamin C Serum", "Beauty & Personal Care", 18.99),
    ("Argan Oil Hair Mask", "Beauty & Personal Care", 15.99),
    ("Electric Toothbrush", "Beauty & Personal Care", 32.99),
    ("Natural Soap Bar Set", "Beauty & Personal Care", 11.99),
    ("Rose Water Face Mist", "Beauty & Personal Care", 9.49),
]

ORDER_STATUSES = ["completed"] * 8 + ["cancelled"] * 1 + ["refunded"] * 1

NUM_CUSTOMERS = 50
NUM_ORDERS = 200
ORDER_LOOKBACK_DAYS = 395  # ~13 months, so "last 3 months" queries are meaningful


def build_customers(rng):
    customers = []
    today = datetime.now()
    for i in range(1, NUM_CUSTOMERS + 1):
        if i <= 30:
            first = rng.choice(ARABIC_FIRST_NAMES)
            last = rng.choice(ARABIC_LAST_NAMES)
        else:
            first = rng.choice(INTL_FIRST_NAMES)
            last = rng.choice(INTL_LAST_NAMES)
        city, country = rng.choice(CITIES)
        email = f"{first.lower()}.{last.lower().replace('-', '')}{i}@example.com"
        signup_date = today - timedelta(days=rng.randint(30, 900))
        customers.append(
            {
                "id": i,
                "name": f"{first} {last}",
                "email": email,
                "city": city,
                "country": country,
                "signup_date": signup_date.strftime("%Y-%m-%d"),
            }
        )
    return customers


def build_products():
    products = []
    for i, (name, category, price) in enumerate(PRODUCTS, start=1):
        products.append({"id": i, "name": name, "category": category, "price": price})
    return products


def build_orders_and_items(rng, customers, products):
    # Not every customer orders — leaves some customers with zero orders,
    # which makes "inactive customers" queries meaningful.
    ordering_customers = rng.sample(customers, k=40)
    today = datetime.now()

    orders, order_items = [], []
    order_id = 1
    item_id = 1
    for _ in range(NUM_ORDERS):
        customer = rng.choice(ordering_customers)
        order_date = today - timedelta(days=rng.randint(0, ORDER_LOOKBACK_DAYS))
        status = rng.choice(ORDER_STATUSES)
        orders.append(
            {
                "id": order_id,
                "customer_id": customer["id"],
                "order_date": order_date.strftime("%Y-%m-%d"),
                "status": status,
            }
        )

        # 1-4 distinct line items per order
        line_products = rng.sample(products, k=rng.randint(1, 4))
        for product in line_products:
            order_items.append(
                {
                    "id": item_id,
                    "order_id": order_id,
                    "product_id": product["id"],
                    "quantity": rng.randint(1, 3),
                    "unit_price": product["price"],
                }
            )
            item_id += 1

        order_id += 1

    return orders, order_items


def create_schema(conn):
    conn.executescript(
        """
        DROP TABLE IF EXISTS order_items;
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS customers;

        CREATE TABLE customers (
            id            INTEGER PRIMARY KEY,
            name          TEXT NOT NULL,
            email         TEXT NOT NULL UNIQUE,
            city          TEXT NOT NULL,
            country       TEXT NOT NULL,
            signup_date   TEXT NOT NULL
        );

        CREATE TABLE products (
            id            INTEGER PRIMARY KEY,
            name          TEXT NOT NULL,
            category      TEXT NOT NULL,
            price         REAL NOT NULL
        );

        CREATE TABLE orders (
            id            INTEGER PRIMARY KEY,
            customer_id   INTEGER NOT NULL REFERENCES customers(id),
            order_date    TEXT NOT NULL,
            status        TEXT NOT NULL CHECK (status IN ('completed', 'cancelled', 'refunded', 'pending'))
        );

        CREATE TABLE order_items (
            id            INTEGER PRIMARY KEY,
            order_id      INTEGER NOT NULL REFERENCES orders(id),
            product_id    INTEGER NOT NULL REFERENCES products(id),
            quantity      INTEGER NOT NULL,
            unit_price    REAL NOT NULL
        );

        CREATE INDEX idx_orders_customer ON orders(customer_id);
        CREATE INDEX idx_orders_date ON orders(order_date);
        CREATE INDEX idx_items_order ON order_items(order_id);
        CREATE INDEX idx_items_product ON order_items(product_id);
        """
    )


def main():
    rng = random.Random(RANDOM_SEED)

    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Removed existing {DB_PATH.name}")

    customers = build_customers(rng)
    products = build_products()
    orders, order_items = build_orders_and_items(rng, customers, products)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    create_schema(conn)

    conn.executemany(
        "INSERT INTO customers (id, name, email, city, country, signup_date) VALUES (:id, :name, :email, :city, :country, :signup_date)",
        customers,
    )
    conn.executemany(
        "INSERT INTO products (id, name, category, price) VALUES (:id, :name, :category, :price)",
        products,
    )
    conn.executemany(
        "INSERT INTO orders (id, customer_id, order_date, status) VALUES (:id, :customer_id, :order_date, :status)",
        orders,
    )
    conn.executemany(
        "INSERT INTO order_items (id, order_id, product_id, quantity, unit_price) VALUES (:id, :order_id, :product_id, :quantity, :unit_price)",
        order_items,
    )
    conn.commit()
    conn.close()

    print(f"Created {DB_PATH} with:")
    print(f"  - {len(customers)} customers")
    print(f"  - {len(products)} products")
    print(f"  - {len(orders)} orders")
    print(f"  - {len(order_items)} order_items")


if __name__ == "__main__":
    main()
