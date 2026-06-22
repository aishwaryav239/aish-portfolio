# pages/analytics.py
# Analytics page — rendered by app.py

import streamlit as st
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from database.db_connection import run_query


def get_monthly_summary():
    return run_query("SELECT * FROM v_monthly_summary")

def get_waste_summary():
    return run_query("SELECT * FROM v_waste_summary")

def get_ingredient_usage():
    return run_query("SELECT * FROM v_ingredient_usage")

def get_cook_frequency():
    return run_query("""
        SELECT cooked_on, recipe_name, servings_cooked
        FROM cook_logs
        ORDER BY cooked_on DESC
        LIMIT 30
    """)


def show_analytics():
    st.title("Analytics")
    st.caption("Track your spending, waste, and cooking patterns over time.")

    tab1, tab2, tab3, tab4 = st.tabs(["💰 Spending", "🗑️ Waste", "🥘 Usage", "📋 Cook history"])

    with tab1:
        st.subheader("Monthly grocery spend (₹)")
        monthly = get_monthly_summary()
        if not monthly.empty:
            st.bar_chart(monthly.set_index("month")["total_spent"])
            st.dataframe(monthly, use_container_width=True, hide_index=True)
        else:
            st.info("No purchase data yet. Add groceries to see spending trends.")

    with tab2:
        st.subheader("Most wasted items")
        waste = get_waste_summary()
        if not waste.empty:
            st.bar_chart(waste.set_index("item_name")["total_cost_wasted"])
            st.dataframe(waste, use_container_width=True, hide_index=True)
        else:
            st.info("No waste logged yet.")

    with tab3:
        st.subheader("Most used ingredients")
        usage = get_ingredient_usage()
        if not usage.empty:
            st.bar_chart(usage.set_index("ingredient_name")["total_used"])
            st.dataframe(usage, use_container_width=True, hide_index=True)
        else:
            st.info("Log some cooks to see ingredient usage.")

    with tab4:
        st.subheader("Recent cooks")
        cooks = get_cook_frequency()
        if not cooks.empty:
            st.dataframe(cooks, use_container_width=True, hide_index=True)
        else:
            st.info("No cooks logged yet.")

    st.divider()
    st.subheader("Connect to Tableau")
    st.info("""
**To connect this data to Tableau:**
1. Open Tableau Desktop → Connect → MySQL
2. Server: localhost | Port: 3306 | Database: ekitchen
3. Username: root | enter your password
4. Use these views for clean dashboards:
   - **v_pantry_status** → current stock + expiry
   - **v_monthly_summary** → monthly spend
   - **v_waste_summary** → most wasted items
   - **v_ingredient_usage** → most used ingredients
    """)
