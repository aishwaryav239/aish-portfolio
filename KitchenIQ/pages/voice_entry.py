# pages/voice_entry.py
# Voice entry page — press a button, speak, app understands and acts.

import streamlit as st
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from services.voice_service import listen_from_microphone, parse_voice_command, execute_voice_action
from services.inventory_service import get_all_item_names


def show_voice_entry():
    st.title("🎤 Voice Entry")
    st.caption("Press the button, speak naturally, and KitchenIQ will understand and act.")

    # ── Examples ────────────────────────────────────────
    with st.expander("💬 What can you say? (examples)", expanded=False):
        st.markdown("""
**Adding groceries:**
- *"I bought 500 grams of chicken for 80 rupees"*
- *"Bought one kg of basmati rice and 200 grams of coriander leaves"*
- *"Purchased 6 eggs and half litre of milk for 60 rupees"*

**Logging a cook:**
- *"I cooked chicken biryani using 200 grams of rice and 250 grams of chicken"*
- *"Made dal for 2 people using 100 grams of lentils and some spices"*

**Logging waste:**
- *"Throw away 30 grams of coriander, it expired"*
- *"Wasted 100 grams of chicken, it spoiled"*
        """)

    st.divider()

    # ── Main listen button ───────────────────────────────
    col1, col2 = st.columns([1, 2])

    with col1:
        listen_btn = st.button("🎤 Start Listening", type="primary", use_container_width=True)
        st.caption("Click, then speak clearly into your microphone.")

    with col2:
        # Show last heard text if available
        if "last_heard" in st.session_state:
            st.info(f"🗣️ You said: **\"{st.session_state['last_heard']}\"**")

    # ── Listen flow ──────────────────────────────────────
    if listen_btn:
        # Clear previous results
        for key in ["last_heard", "parsed_action", "voice_error"]:
            st.session_state.pop(key, None)

        # Step 1: Listen
        with st.spinner("🎤 Listening... speak now!"):
            text, err = listen_from_microphone(timeout=8)

        if err:
            st.session_state["voice_error"] = err
        else:
            st.session_state["last_heard"] = text

            # Step 2: Parse with Ollama
            with st.spinner("🧠 Understanding your command..."):
                pantry_names = get_all_item_names()
                action, parse_err = parse_voice_command(text, pantry_names)

            if parse_err:
                st.session_state["voice_error"] = parse_err
            else:
                st.session_state["parsed_action"] = action
        st.rerun()

    # ── Show error if any ────────────────────────────────
    if "voice_error" in st.session_state:
        st.error(f"❌ {st.session_state['voice_error']}")

    # ── Show parsed action for confirmation ─────────────
    if "parsed_action" in st.session_state:
        action = st.session_state["parsed_action"]
        action_type = action.get("action", "unknown")

        if action_type == "unknown":
            st.warning(f"🤔 Could not understand: {action.get('message', 'Try again.')}")

        else:
            st.success(f"✅ Understood as: **{action_type.replace('_', ' ').title()}**")

            # Show what was understood in a clean preview
            st.markdown("**Here's what I understood — confirm to save:**")

            if action_type == "add_grocery":
                for item in action.get("items", []):
                    st.markdown(f"- **{item.get('name')}** — {item.get('qty')} {item.get('unit')} | ₹{item.get('cost', 0)} | Category: {item.get('category', 'other')}")

            elif action_type == "log_cook":
                st.markdown(f"- **Recipe:** {action.get('recipe_name')} ({action.get('servings', 2)} servings)")
                for ing in action.get("ingredients", []):
                    st.markdown(f"  - {ing.get('qty')} {ing.get('unit')} of {ing.get('name')}")

            elif action_type == "log_waste":
                for item in action.get("items", []):
                    st.markdown(f"- **{item.get('name')}** — {item.get('qty')} {item.get('unit')} | Reason: {item.get('reason', 'expired')}")

            st.divider()

            # Confirm / Cancel buttons
            c1, c2, c3 = st.columns([1, 1, 2])
            confirm = c1.button("✅ Confirm & Save", type="primary")
            cancel  = c2.button("❌ Cancel")

            if confirm:
                with st.spinner("Saving..."):
                    msg, err = execute_voice_action(action, get_all_item_names())
                if err:
                    st.error(f"❌ {err}")
                else:
                    st.success(msg)
                    # Clear session state after saving
                    for key in ["last_heard", "parsed_action", "voice_error"]:
                        st.session_state.pop(key, None)
                    st.balloons()
                    st.rerun()

            if cancel:
                for key in ["last_heard", "parsed_action", "voice_error"]:
                    st.session_state.pop(key, None)
                st.rerun()

    # ── History of voice actions ─────────────────────────
    st.divider()
    st.subheader("Recent voice actions")
    if "voice_history" not in st.session_state:
        st.session_state["voice_history"] = []

    if st.session_state["voice_history"]:
        for entry in reversed(st.session_state["voice_history"][-5:]):
            st.markdown(f"- {entry}")
    else:
        st.caption("Nothing saved via voice yet.")
