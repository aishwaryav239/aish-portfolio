# services/recipe_service.py
# Business logic for saving cook logs and retrieving cook history.

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'database'))
from db_connection import run_query, run_write, run_write_returning
from inventory_service import deduct_from_pantry


def log_cook(recipe_name, servings_cooked, cooked_on, ingredients_used):
    """
    Save a cook session and deduct all ingredients from pantry.
    ingredients_used = list of dicts: [{"name": ..., "qty_used": ..., "unit": ...}]
    """
    cook_id = run_write_returning("""
        INSERT INTO cook_logs (recipe_name, servings_cooked, cooked_on)
        VALUES (%s, %s, %s)
    """, (recipe_name, servings_cooked, cooked_on))

    for ing in ingredients_used:
        run_write("""
            INSERT INTO cook_log_ingredients
                (cook_log_id, ingredient_name, quantity_used, unit)
            VALUES (%s, %s, %s, %s)
        """, (cook_id, ing["name"], ing["qty_used"], ing["unit"]))

        deduct_from_pantry(ing["name"], ing["qty_used"])

    return cook_id


def get_cook_history():
    """All past cook sessions, newest first."""
    return run_query("""
        SELECT cooked_on, recipe_name, servings_cooked, notes
        FROM cook_logs
        ORDER BY cooked_on DESC
    """)


def get_cook_detail(cook_log_id):
    """Ingredients used in a specific cook session."""
    return run_query("""
        SELECT ingredient_name, quantity_used, unit
        FROM cook_log_ingredients
        WHERE cook_log_id = %s
    """, params=(cook_log_id,))
