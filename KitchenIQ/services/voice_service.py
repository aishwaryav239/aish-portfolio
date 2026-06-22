# services/voice_service.py
# Listens to the microphone, converts speech to text,
# then uses local Ollama to understand what the user said
# and returns a structured action.

import speech_recognition as sr
import requests
import json


OLLAMA_URL  = "http://localhost:11434/api/generate"
MODEL_NAME  = "llama3.2:1b"


# ─────────────────────────────────────────────
# STEP 1 — CAPTURE SPEECH FROM MICROPHONE
# ─────────────────────────────────────────────

def listen_from_microphone(timeout=8):
    """
    Opens the microphone, listens until the user stops speaking,
    and returns (text, error).
    timeout = how many seconds to wait for speech before giving up.
    """
    recognizer = sr.Recognizer()
    recognizer.energy_threshold    = 300   # sensitivity — lower = picks up quieter speech
    recognizer.pause_threshold     = 1.2   # seconds of silence before considering speech done
    recognizer.dynamic_energy_threshold = True

    try:
        with sr.Microphone() as source:
            # Adjust for ambient noise for 1 second
            recognizer.adjust_for_ambient_noise(source, duration=1)
            # Listen — phrase_time_limit stops listening after 15s max
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=15)

        # Use Google's free speech-to-text (needs internet, free, very accurate)
        text = recognizer.recognize_google(audio, language="en-IN")
        return text, None

    except sr.WaitTimeoutError:
        return None, "No speech detected. Please try again."
    except sr.UnknownValueError:
        return None, "Could not understand the audio. Please speak clearly and try again."
    except sr.RequestError:
        return None, "Speech recognition service unavailable. Check your internet connection."
    except OSError:
        return None, "Microphone not found. Make sure your microphone is connected and allowed."
    except Exception as e:
        return None, f"Microphone error: {str(e)}"


# ─────────────────────────────────────────────
# STEP 2 — PARSE SPEECH USING OLLAMA
# ─────────────────────────────────────────────

def parse_voice_command(text, pantry_item_names=None):
    """
    Sends the spoken text to Ollama and asks it to extract
    a structured action from natural language.

    Returns (action_dict, error).
    action_dict has keys:
      - action: "add_grocery" | "log_cook" | "log_waste" | "unknown"
      - For add_grocery:  items = [{"name", "qty", "unit", "cost", "category"}]
      - For log_cook:     recipe_name, servings, ingredients = [{"name","qty","unit"}]
      - For log_waste:    items = [{"name", "qty", "unit", "reason"}]
    """
    pantry_hint = ""
    if pantry_item_names:
        pantry_hint = f"\nKnown pantry items for reference: {', '.join(pantry_item_names[:20])}"

    prompt = f"""You are a kitchen assistant that extracts structured data from natural speech.

The user said: "{text}"{pantry_hint}

Determine what action the user wants to perform and extract the details.
Actions can be:
- add_grocery: user bought/purchased something
- log_cook: user cooked something
- log_waste: user threw away / wasted / expired something
- unknown: cannot determine

Respond ONLY with a valid JSON object. No explanation. No markdown. No extra text.

For add_grocery:
{{"action": "add_grocery", "items": [{{"name": "Chicken", "qty": 500, "unit": "g", "cost": 80, "category": "meat"}}]}}

For log_cook:
{{"action": "log_cook", "recipe_name": "Biryani", "servings": 2, "ingredients": [{{"name": "Rice", "qty": 200, "unit": "g"}}, {{"name": "Chicken", "qty": 250, "unit": "g"}}]}}

For log_waste:
{{"action": "log_waste", "items": [{{"name": "Coriander", "qty": 50, "unit": "g", "reason": "expired"}}]}}

For unknown:
{{"action": "unknown", "message": "Could not understand the command"}}

Rules:
- If unit is not mentioned, guess from context (liquids=ml, powders/solids=g, whole items=pcs)
- If cost is not mentioned, use 0
- If category is not mentioned, guess from item name (chicken/fish/meat=meat, rice/wheat=grain, etc.)
- If servings not mentioned for cook, use 2
- Always return valid JSON"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 500}
            },
            timeout=60
        )

        if response.status_code != 200:
            return None, f"Ollama error {response.status_code}"

        raw = response.json().get("response", "").strip()

        # Extract JSON object from response
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start == -1 or end == 0:
            return None, "Could not parse Ollama response. Try again."

        action = json.loads(raw[start:end])
        return action, None

    except json.JSONDecodeError:
        return None, "Ollama returned invalid JSON. Try again."
    except requests.exceptions.Timeout:
        return None, "Ollama took too long. Try again."
    except requests.exceptions.ConnectionError:
        return None, "Ollama is not running. Run 'ollama serve' in terminal."
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"


# ─────────────────────────────────────────────
# STEP 3 — EXECUTE THE ACTION
# ─────────────────────────────────────────────

def execute_voice_action(action_dict, pantry_item_names=None):
    """
    Takes a parsed action dict and calls the right service functions.
    Returns (success_message, error_message).
    """
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from services.inventory_service import (
        add_pantry_item, get_item_id_by_name,
        log_purchase, log_waste
    )
    from services.recipe_service import log_cook
    from datetime import date, timedelta

    action = action_dict.get("action")

    if action == "add_grocery":
        items = action_dict.get("items", [])
        if not items:
            return None, "No items found in voice command."

        messages = []
        for item in items:
            name     = item.get("name", "").strip()
            qty      = float(item.get("qty", 0))
            unit     = item.get("unit", "g")
            cost     = float(item.get("cost", 0))
            category = item.get("category", "other")

            if not name or qty <= 0:
                continue

            # Default shelf life by category
            shelf_life_map = {
                "meat": 2, "vegetable": 5, "dairy": 7,
                "grain": 365, "spice": 180, "condiment": 30, "oil": 180
            }
            shelf_life  = shelf_life_map.get(category, 7)
            today       = date.today()
            expiry_date = today + timedelta(days=shelf_life)
            cost_per_unit = round(cost / qty, 4) if qty > 0 else 0

            add_pantry_item(name, category, qty, unit, shelf_life,
                            today, expiry_date, cost_per_unit)

            item_id = get_item_id_by_name(name)
            if item_id:
                log_purchase(item_id, qty, unit, cost, today)

            messages.append(f"✅ Added {qty}{unit} of {name}")

        return "\n".join(messages) if messages else None, \
               None if messages else "No valid items to add."

    elif action == "log_cook":
        recipe_name  = action_dict.get("recipe_name", "Unknown")
        servings     = int(action_dict.get("servings", 2))
        ingredients  = action_dict.get("ingredients", [])

        if not ingredients:
            return None, "No ingredients found in voice command."

        ing_list = [
            {"name": i["name"], "qty_used": float(i["qty"]), "unit": i["unit"]}
            for i in ingredients if i.get("name") and float(i.get("qty", 0)) > 0
        ]

        if not ing_list:
            return None, "No valid ingredients found."

        log_cook(recipe_name, servings, date.today(), ing_list)
        ing_summary = ", ".join([f"{i['qty_used']}{i['unit']} {i['name']}" for i in ing_list])
        return f"✅ Logged cook: {recipe_name} using {ing_summary}", None

    elif action == "log_waste":
        items = action_dict.get("items", [])
        if not items:
            return None, "No waste items found in voice command."

        messages = []
        for item in items:
            name   = item.get("name", "").strip()
            qty    = float(item.get("qty", 0))
            unit   = item.get("unit", "g")
            reason = item.get("reason", "expired")
            if name and qty > 0:
                log_waste(name, qty, unit, reason)
                messages.append(f"✅ Logged waste: {qty}{unit} of {name} ({reason})")

        return "\n".join(messages) if messages else None, \
               None if messages else "No valid waste items found."

    elif action == "unknown":
        return None, f"Could not understand: {action_dict.get('message', 'Please try again.')}"

    else:
        return None, "Unknown action type returned by AI."
