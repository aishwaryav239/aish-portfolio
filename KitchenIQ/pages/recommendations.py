# pages/recommendations.py
# AI-powered recipe suggestions using local Ollama LLM

import streamlit as st
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from services.inventory_service import get_pantry
from services.recommendation_service import check_ollama_running, get_ai_recipe_suggestions


def show_recommendations():
    st.title("What can you cook?")
    st.caption("A local AI suggests recipes based on what is currently in your pantry. No internet or API key needed.")

    # ── Ollama status check ──────────────────────────────
    ollama_ok, ollama_err = check_ollama_running()
    if not ollama_ok:
        st.error("🦙 Ollama is not running")
        st.markdown(f"""
**{ollama_err}**

---
**First time setup (do this once):**

**1.** Download and install Ollama from **https://ollama.com**

**2.** Open Command Prompt and download the AI model:
```
ollama pull llama3.2
```
This is a ~2GB download. Wait for it to finish.

**3.** Ollama starts automatically after install. If it stopped, run:
```
ollama serve
```

**4.** Refresh this page — the status will turn green.
        """)
        return

    st.success("🦙 Ollama is running — ready to suggest recipes")

    # ── Pantry check ─────────────────────────────────────
    pantry_df = get_pantry()
    if pantry_df.empty:
        st.info("Your pantry is empty. Go to 'Add Groceries' first, then come back here.")
        return

    # Show pantry summary
    with st.expander("📦 Your current pantry", expanded=False):
        st.dataframe(
            pantry_df[["name", "current_qty", "unit", "expiry_status"]],
            use_container_width=True, hide_index=True
        )

    # ── Preference filters ───────────────────────────────
    c1, c2 = st.columns(2)
    cuisine_pref = c1.selectbox("Cuisine preference",
        ["Any", "South Indian", "North Indian", "Indian",
         "Continental", "Chinese", "Italian", "Mexican"])
    meal_type = c2.selectbox("Meal type",
        ["Any", "Breakfast", "Lunch", "Dinner", "Snack"])

    extra_note = st.text_input(
        "Any special request? (optional)",
        placeholder="e.g. quick under 30 mins, no spicy, high protein, use expiring items"
    )

    # Auto-highlight expiring items
    expiring = pantry_df[pantry_df["expiry_status"].isin(["expired", "expiring_soon"])]
    if not expiring.empty:
        exp_names = ", ".join(expiring["name"].tolist())
        st.warning(f"⚠️ Expiring soon: **{exp_names}** — the AI will prioritize these.")
        if not extra_note:
            extra_note = f"Prioritize using these expiring items: {exp_names}"

    st.info("⏳ The AI runs on your PC — first response may take 30–60 seconds depending on your hardware.")

    if st.button("🦙 Suggest recipes from my pantry", type="primary"):
        with st.spinner("Your local AI is thinking... this may take up to a minute."):
            recipes, error = get_ai_recipe_suggestions(
                pantry_df, cuisine_pref, meal_type, extra_note
            )
            if error:
                st.error(f"{error}")
            else:
                st.session_state["ai_recipes"] = recipes

    # ── Display results ──────────────────────────────────
    if "ai_recipes" in st.session_state:
        st.divider()
        st.subheader(f"🍽️ {len(st.session_state['ai_recipes'])} recipes suggested for you")

        for i, recipe in enumerate(st.session_state["ai_recipes"]):
            missing = recipe.get("missing_ingredients", [])
            label = "✅ Can cook now!" if not missing else f"🛒 Need {len(missing)} item(s)"

            with st.expander(
                f"**{recipe.get('name', 'Recipe')}**  |  "
                f"{recipe.get('cuisine', 'Indian')}  |  "
                f"⏱ {recipe.get('time_mins', '?')} mins  |  "
                f"🍽 {recipe.get('servings', '?')} servings  |  {label}",
                expanded=(i == 0)
            ):
                c1, c2 = st.columns(2)

                with c1:
                    st.markdown("**✅ Ingredients you have:**")
                    for ing in recipe.get("match_ingredients", []):
                        st.markdown(f"- {ing}")

                with c2:
                    if missing:
                        st.markdown("**🛒 Need to buy:**")
                        for ing in missing:
                            st.markdown(f"- {ing}")
                    else:
                        st.success("You have everything to make this!")

                st.markdown("**👨‍🍳 Steps:**")
                for step in recipe.get("steps", []):
                    st.markdown(f"{step}")

                if recipe.get("tip"):
                    st.info(f"💡 Tip: {recipe['tip']}")
