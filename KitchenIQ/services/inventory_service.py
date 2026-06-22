# services/inventory_service.py
# All business logic for pantry management and grocery purchases.
# Pages import from here — never from db_connection directly.

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'database'))
from db_connection import run_query, run_write, run_write_returning


# ─────────────────────────────────────────────
# PANTRY
# ─────────────────────────────────────────────

def get_pantry():
    """All pantry items with expiry status."""
    return run_query("SELECT * FROM v_pantry_status")


def get_all_item_names():
    """Plain list of item names — used as hints in text inputs."""
    df = run_query("SELECT name FROM pantry_items ORDER BY name")
    return df["name"].tolist()


def get_expiring_soon(days=3):
    """Items expiring within the next N days."""
    return run_query("""
        SELECT name, current_qty, unit, expiry_date, days_until_expiry
        FROM v_pantry_status
        WHERE expiry_status IN ('expired', 'expiring_soon')
          AND days_until_expiry <= %s
        ORDER BY days_until_expiry ASC
    """, params=(days,))


def add_pantry_item(name, category, qty, unit, shelf_life_days,
                    purchase_date, expiry_date, cost_per_unit):
    """
    Add item to pantry. If item already exists (same name),
    quantity is added on top — not replaced.
    """
    run_write("""
        INSERT INTO pantry_items
            (name, category, current_qty, unit, shelf_life_days,
             purchase_date, expiry_date, cost_per_unit)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            current_qty = current_qty + VALUES(current_qty),
            updated_at  = CURRENT_TIMESTAMP
    """, (name, category, qty, unit, shelf_life_days,
          purchase_date, expiry_date, cost_per_unit))


def deduct_from_pantry(item_name, qty_used):
    """
    Subtract qty_used from pantry. Quantity never goes below 0.
    Called automatically when a cook is logged.
    """
    run_write("""
        UPDATE pantry_items
        SET current_qty = GREATEST(current_qty - %s, 0),
            updated_at  = CURRENT_TIMESTAMP
        WHERE name = %s
    """, (qty_used, item_name))


def log_waste(item_name, qty_wasted, unit, reason="expired"):
    """Record wasted food and deduct from pantry."""
    df = run_query(
        "SELECT cost_per_unit FROM pantry_items WHERE name = %s",
        params=(item_name,)
    )
    cost = float(df["cost_per_unit"].iloc[0]) * qty_wasted if not df.empty else 0

    run_write("""
        INSERT INTO waste_log
            (item_name, quantity_wasted, unit, reason, wasted_on, estimated_cost)
        VALUES (%s, %s, %s, %s, CURDATE(), %s)
    """, (item_name, qty_wasted, unit, reason, cost))

    deduct_from_pantry(item_name, qty_wasted)


# ─────────────────────────────────────────────
# GROCERY PURCHASES
# ─────────────────────────────────────────────

def log_purchase(item_id, qty, unit, cost, purchase_date, shop_name=""):
    """Record a grocery purchase and top up the pantry quantity."""
    run_write("""
        INSERT INTO grocery_purchases
            (item_id, quantity_bought, unit, cost, purchase_date, shop_name)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (item_id, qty, unit, cost, purchase_date, shop_name))

    run_write("""
        UPDATE pantry_items
        SET current_qty = current_qty + %s,
            updated_at  = CURRENT_TIMESTAMP
        WHERE id = %s
    """, (qty, item_id))


def get_item_id_by_name(name):
    """Return the pantry item ID for a given name, or None."""
    df = run_query("SELECT id FROM pantry_items WHERE name = %s", params=(name,))
    return int(df["id"].iloc[0]) if not df.empty else None


def get_purchase_history():
    """Full purchase history with item names."""
    return run_query("""
        SELECT gp.purchase_date, p.name AS item,
               gp.quantity_bought, gp.unit, gp.cost, gp.shop_name
        FROM grocery_purchases gp
        JOIN pantry_items p ON p.id = gp.item_id
        ORDER BY gp.purchase_date DESC
    """)
