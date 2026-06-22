# pages/recipes.py
# Log a Cook page — rendered by app.py

import streamlit as st
from datetime import date
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from services.recipe_service import log_cook, get_cook_history
from services.inventory_service import get_all_item_names


def show_log_cook():
    st.title("Log a cook")
    st.caption("Record what you cooked and how much of each ingredient you used. Pantry updates automatically.")

    with st.form("cook_form"):
        c1, c2, c3 = st.columns(3)
        recipe_name   = c1.text_input("Recipe name", placeholder="e.g. Chicken Biryani")
        servings      = c2.number_input("Servings cooked", min_value=1, value=2)
        cook_date     = c3.date_input("Date cooked", value=date.today())

        st.markdown("**Ingredients used**")
        st.caption("Type each ingredient name and how much you used.")

        if "num_ing_rows" not in st.session_state:
            st.session_state["num_ing_rows"] = 3

        pantry_names = get_all_item_names()
        hint = "In pantry: " + ", ".join(pantry_names[:8]) + ("..." if len(pantry_names) > 8 else "") \
               if pantry_names else "Add groceries first"

        ingredients_used = []
        for i in range(st.session_state["num_ing_rows"]):
            c1, c2, c3 = st.columns([3, 1, 1])
            ing_name = c1.text_input(f"Ingredient {i+1}", placeholder="e.g. Basmati rice",
                                     key=f"ing_{i}", help=hint)
            ing_qty  = c2.number_input("Qty", min_value=0.0, value=0.0, key=f"qty_{i}")
            ing_unit = c3.selectbox("Unit", ["g","kg","ml","l","pcs","tsp","tbsp"], key=f"unit_{i}")
            if ing_name.strip() and ing_qty > 0:
                ingredients_used.append({
                    "name": ing_name.strip(),
                    "qty_used": ing_qty,
                    "unit": ing_unit
                })

        ca, cb = st.columns(2)
        add_row  = ca.form_submit_button("+ Add row")
        save_btn = cb.form_submit_button("✅ Save cook log")

        if add_row:
            st.session_state["num_ing_rows"] += 1
            st.rerun()

        if save_btn:
            if not recipe_name.strip():
                st.error("Please enter a recipe name.")
            elif not ingredients_used:
                st.error("Add at least one ingredient with a quantity greater than 0.")
            else:
                log_cook(recipe_name.strip(), servings, cook_date, ingredients_used)
                st.session_state["num_ing_rows"] = 3
                st.success(f"Cook logged! Pantry has been updated.")
                st.rerun()

    st.divider()
    st.subheader("Cook history")
    hist = get_cook_history()
    if not hist.empty:
        st.dataframe(hist, use_container_width=True, hide_index=True)
    else:
        st.info("No cooks logged yet.")
