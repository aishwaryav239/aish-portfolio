# pages/inventory.py
# Pantry view and Add Groceries — rendered by app.py

import streamlit as st
from datetime import date, timedelta
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from services.inventory_service import (
    get_pantry, get_all_item_names, add_pantry_item,
    log_purchase, get_item_id_by_name,
    get_purchase_history, log_waste
)


def show_pantry():
    st.title("Your pantry")
    st.caption("Everything you currently have, with quantities and expiry status.")

    df = get_pantry()

    if df.empty:
        st.info("Your pantry is empty. Go to 'Add Groceries' to get started.")
        return

    # Summary metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total items", len(df))
    c2.metric("Expiring in 3 days",
              len(df[df["expiry_status"].isin(["expired", "expiring_soon"])]))
    c3.metric("Categories", df["category"].nunique())
    c4.metric("Expired", len(df[df["expiry_status"] == "expired"]))

    st.divider()

    # Category filter
    cats = ["All"] + sorted(df["category"].dropna().unique().tolist())
    chosen = st.selectbox("Filter by category", cats)
    if chosen != "All":
        df = df[df["category"] == chosen]

    # Colour expiry status
    def highlight_expiry(val):
        if val == "expired":       return "background-color:#FCEBEB;color:#A32D2D"
        if val == "expiring_soon": return "background-color:#FAEEDA;color:#633806"
        if val == "ok":            return "background-color:#EAF3DE;color:#27500A"
        return ""

    styled = df[["name","category","current_qty","unit",
                 "expiry_date","expiry_status","days_until_expiry"]] \
               .style.applymap(highlight_expiry, subset=["expiry_status"])
    st.dataframe(styled, use_container_width=True, hide_index=True)

    # Log waste section
    st.divider()
    st.subheader("Log wasted food")
    st.caption("Use this when something expires or gets thrown away.")
    w1, w2, w3, w4 = st.columns(4)
    item_names = get_all_item_names()
    w_item   = w1.selectbox("Item", item_names, key="waste_item")
    w_qty    = w2.number_input("Quantity", min_value=0.1, value=10.0, key="waste_qty")
    w_unit   = w3.selectbox("Unit", ["g","kg","ml","l","pcs","tsp","tbsp"], key="waste_unit")
    w_reason = w4.selectbox("Reason", ["expired","spoiled","dropped","other"])
    if st.button("Log waste"):
        log_waste(w_item, w_qty, w_unit, w_reason)
        st.success(f"Logged {w_qty}{w_unit} of {w_item} as wasted.")
        st.rerun()


def show_add_groceries():
    st.title("Add groceries")
    st.caption("Add items you just bought. They are added to your pantry immediately.")

    with st.form("grocery_form"):
        c1, c2 = st.columns(2)
        name     = c1.text_input("Item name", placeholder="e.g. Basmati rice")
        category = c2.selectbox("Category",
                    ["grain","spice","vegetable","meat","dairy","condiment","oil","other"])

        c3, c4, c5 = st.columns(3)
        qty   = c3.number_input("Quantity bought", min_value=0.1, value=500.0)
        unit  = c4.selectbox("Unit", ["g","kg","ml","l","pcs","tsp","tbsp"])
        cost  = c5.number_input("Total cost (₹)", min_value=0.0, value=50.0)

        c6, c7, c8 = st.columns(3)
        purchase_date = c6.date_input("Purchase date", value=date.today())
        shelf_life    = c7.number_input("Shelf life (days)", min_value=1, value=7)
        shop          = c8.text_input("Shop name", placeholder="e.g. Big Bazaar")

        expiry_date = purchase_date + timedelta(days=int(shelf_life))
        st.caption(f"Calculated expiry date: **{expiry_date}**")

        submitted = st.form_submit_button("Add to pantry")
        if submitted:
            if not name:
                st.error("Please enter an item name.")
            else:
                cost_per_unit = round(cost / qty, 4) if qty > 0 else 0
                add_pantry_item(name, category, qty, unit, shelf_life,
                                purchase_date, expiry_date, cost_per_unit)
                item_id = get_item_id_by_name(name)
                if item_id:
                    log_purchase(item_id, qty, unit, cost, purchase_date, shop)
                st.success(f"Added {qty}{unit} of **{name}** to pantry!")
                st.rerun()

    st.divider()
    st.subheader("Purchase history")
    hist = get_purchase_history()
    if not hist.empty:
        st.dataframe(hist, use_container_width=True, hide_index=True)
    else:
        st.info("No purchases logged yet.")
