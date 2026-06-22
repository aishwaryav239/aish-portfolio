# services/recommendation_service.py
# Calls a locally running Ollama LLM to suggest recipes.
# No API key needed. No internet needed. Completely free.
#
# SETUP (do this once):
# 1. Download Ollama from https://ollama.com and install it
# 2. Open terminal and run:  ollama pull llama3.2
# 3. That's it — Ollama runs as a background service automatically

import requests
import json

# Ollama runs locally on this port by default — no need to change this
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2"   # change to "llama3" or "mistral" if you pulled a different model


def check_ollama_running():
    """
    Check if Ollama is running on this machine.
    Returns (True, None) if running, (False, help message) if not.
    """
    try:
        response = requests.get("http://localhost:11434", timeout=3)
        return True, None
    except requests.exceptions.ConnectionError:
        return False, (
            "Ollama is not running.\n\n"
            "Fix:\n"
            "1. Make sure you installed Ollama from https://ollama.com\n"
            "2. Open Command Prompt and run:  ollama serve\n"
            "3. Then refresh this page"
        )
    except Exception as e:
        return False, f"Cannot reach Ollama: {str(e)}"


def get_ai_recipe_suggestions(pantry_df, cuisine_pref="Any", meal_type="Any", extra_note=""):
    """
    Takes a pantry DataFrame and returns AI-suggested recipes using local Ollama LLM.
    Returns (recipes_list, error_message).
    On success: (list, None). On failure: (None, error_string).
    """
    if pantry_df.empty:
        return None, "Pantry is empty. Add groceries first."

    # Check Ollama is running before trying
    ok, err = check_ollama_running()
    if not ok:
        return None, err

    # Build ingredient list from pantry
    ing_lines = [
        f"{row['name']}: {row['current_qty']} {row['unit']}"
        for _, row in pantry_df.iterrows()
    ]
    pantry_text = "\n".join(ing_lines)

    # Build filter string
    filters = []
    if cuisine_pref != "Any": filters.append(f"cuisine: {cuisine_pref}")
    if meal_type    != "Any": filters.append(f"meal type: {meal_type}")
    if extra_note:             filters.append(extra_note)
    filter_str = ". ".join(filters) if filters else "any cuisine"

    prompt = f"""You are a helpful kitchen assistant.
The user has these ingredients in their pantry:
{pantry_text}

Suggest 4 realistic recipes they can cook using mostly these ingredients ({filter_str}).

Respond ONLY with a valid JSON array. No explanation before or after. No markdown. No extra text.
Use exactly this format:
[
  {{
    "name": "Recipe Name",
    "cuisine": "cuisine type",
    "time_mins": 30,
    "servings": 2,
    "match_ingredients": ["ingredient1", "ingredient2"],
    "missing_ingredients": ["ingredient3"],
    "steps": ["Step 1: ...", "Step 2: ...", "Step 3: ..."],
    "tip": "One useful cooking tip"
  }}
]"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,       # get full response at once
                "options": {
                    "temperature": 0.7,
                    "num_predict": 2000
                }
            },
            timeout=120    # local LLMs can be slow — give it 2 minutes
        )

        if response.status_code != 200:
            return None, f"Ollama error {response.status_code}: {response.text[:300]}"

        raw = response.json().get("response", "").strip()

        # Extract JSON from the response
        # Sometimes the model adds text before/after the JSON — find the array
        start = raw.find("[")
        end   = raw.rfind("]") + 1
        if start == -1 or end == 0:
            return None, (
                "The model did not return valid JSON. Try clicking the button again — "
                "LLMs sometimes need a retry."
            )

        json_str = raw[start:end]
        recipes = json.loads(json_str)

        # Validate it's a list with at least one recipe
        if not isinstance(recipes, list) or len(recipes) == 0:
            return None, "Model returned an empty recipe list. Please try again."

        return recipes, None

    except json.JSONDecodeError as e:
        return None, (
            f"Could not parse the model's response as JSON: {e}\n"
            "Try clicking the button again — this sometimes fixes it."
        )
    except requests.exceptions.Timeout:
        return None, (
            "The model took too long to respond (over 2 minutes).\n"
            "This can happen if your PC is slow. Try a smaller model:\n"
            "Run:  ollama pull tinyllama  then change MODEL_NAME in recommendation_service.py"
        )
    except requests.exceptions.ConnectionError:
        return None, (
            "Lost connection to Ollama mid-request.\n"
            "Run 'ollama serve' in your terminal and try again."
        )
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"
