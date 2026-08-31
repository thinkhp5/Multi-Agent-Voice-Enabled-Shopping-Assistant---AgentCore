"""
Static demo data standing in for real catalog/order backends.

In production, swap these dict lookups inside mcp_server/server.py for real
calls to your product catalog service and order management system — the
MCP tool contract (function names + schemas) doesn't need to change.
"""

PRODUCT_CATALOG = [
    {
        "id": "P100",
        "name": "Bose QC45 Headphones",
        "category": "audio",
        "price": 329,
        "description": "Wireless noise-cancelling over-ear headphones, 24-hour battery.",
    },
    {
        "id": "P101",
        "name": "Sony WH-1000XM5",
        "category": "audio",
        "price": 250,
        "description": "Industry-leading ANC, 30-hour battery, wireless headphones.",
    },
    {
        "id": "P102",
        "name": "boAt Airdopes 141",
        "category": "audio",
        "price": 100,
        "description": "Budget-friendly wireless earbuds, 42-hour total playback.",
    },
    {
        "id": "P200",
        "name": "iPhone 15 Pro Max",
        "category": "phones",
        "price": 1600,
        "description": "A17 Pro chip, titanium frame, 48MP camera.",
    },
    {
        "id": "P201",
        "name": "Samsung Galaxy S24 Ultra",
        "category": "phones",
        "price": 1800,
        "description": "200MP camera, Galaxy AI, built-in S Pen.",
    },
    {
        "id": "P300",
        "name": "Air Jordan 1 Retro High OG",
        "category": "footwear",
        "price": 180,
        "description": "Classic high-top basketball sneaker.",
    },
]

ORDER_DB = {
    "ORD101": {
        "order_id": "ORD101",
        "customer_email": "alex@example.com",
        "product_id": "P300",
        "product_name": "Air Jordan 1 Retro High OG",
        "status": "Shipped",
        "eta": "2026-09-05",
        "notes": None,
    },
    "ORD102": {
        "order_id": "ORD102",
        "customer_email": "jordan@example.com",
        "product_id": "P100",
        "product_name": "Bose QC45 Headphones",
        "status": "Delayed",
        "eta": "2026-09-10",
        "notes": "Delayed due to weather at regional hub.",
    },
}

SUPPORT_ESCALATION_POLICY = {
    "HIGH": "Customer contacted within 4 hours.",
    "MEDIUM": "Customer contacted within 24 hours.",
    "LOW": "Customer contacted within 3 business days.",
}
