# app.py — Main entry point
# This file only handles navigation and the connection check.
# All actual page logic lives in pages/ and services/.

import streamlit as st
import sys, os

# Make sure subfolders are importable
sys.path.append(os.path.dirname(__file__))

from database.db_connection import test_connection
from services.inventory_service import get_expiring_soon

st.set_page_config(
    page_title="KitchenIQ",
    page_icon="🍳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# CONNECTION CHECK
# Shows a clear fix-it screen instead of crashing
# ─────────────────────────────────────────────
ok, err = test_connection()
if not ok:
    st.error("🔌 Cannot connect to MySQL")
    st.markdown(f"""
**Reason:** {err}

---
**Checklist:**

1. **Is MySQL running?**  
   Windows → open Services → find MySQL80 → click Start

2. **Is the password correct?**  
   Open `database/db_connection.py` → update `password` field → save → refresh this tab

3. **Is the database created?**  
   Run in terminal: `python database/setup.py`  
   Then refresh this tab.
""")
    st.stop()

# ─────────────────────────────────────────────
# EXPIRY ALERT BANNER (shown on every page)
# ─────────────────────────────────────────────
try:
    expiring = get_expiring_soon(days=3)
    if not expiring.empty:
        names = ", ".join(expiring["name"].tolist())
        st.warning(f"⚠️ Items expiring soon: **{names}** — cook these first!")
except Exception:
    pass

# ─────────────────────────────────────────────
# SIDEBAR NAVIGATION
# ─────────────────────────────────────────────
st.sidebar.title("🍳 KitchenIQ")
page = st.sidebar.radio("Navigate", [
    "📦 Pantry",
    "🛒 Add Groceries",
    "🎤 Voice Entry",
    "🍽️ Recipe Suggestions",
    "📝 Log a Cook",
    "📊 Analytics",
])

# ─────────────────────────────────────────────
# PAGE ROUTING — each page is its own file
# ─────────────────────────────────────────────
if page == "📦 Pantry":
    from pages.inventory import show_pantry
    show_pantry()

elif page == "🛒 Add Groceries":
    from pages.inventory import show_add_groceries
    show_add_groceries()

elif page == "🎤 Voice Entry":
    from pages.voice_entry import show_voice_entry
    show_voice_entry()

elif page == "🍽️ Recipe Suggestions":
    from pages.recommendations import show_recommendations
    show_recommendations()

elif page == "📝 Log a Cook":
    from pages.recipes import show_log_cook
    show_log_cook()

elif page == "📊 Analytics":
    from pages.analytics import show_analytics
    show_analytics()
