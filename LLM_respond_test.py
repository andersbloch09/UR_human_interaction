import requests
import json

# ---- CONFIG ----
LLM_URL = "http://172.27.15.38:11434/api/generate"  # replace with your LLM server URL
MODEL_NAME = "phi4:latest"  # or whatever your model is
SYSTEM_PROMPT = "You are a helpful assistant."

# ---- TEST PROMPT ----
user_prompt = "Hello! Can you respond with a short test message?"

# ---- BUILD MESSAGE ----
message = {
    "model": MODEL_NAME,
    "prompt": SYSTEM_PROMPT + "\n" + user_prompt,
    "stream": False  # False for single response, True if streaming supported
}

try:
    response = requests.post(
        LLM_URL,
        data=json.dumps(message),
        headers={"Content-Type": "application/json"},
        timeout=15  # seconds
    )

    response.raise_for_status()  # raise error for bad HTTP codes

    # Try parsing JSON
    result = response.json()
    print("LLM Response:", result)

except requests.exceptions.ConnectTimeout:
    print("Error: Connection timed out. The server may be unreachable.")
except requests.exceptions.ConnectionError:
    print("Error: Could not connect to the LLM server. Check IP/network.")
except requests.exceptions.HTTPError as e:
    print(f"HTTP error: {e}")
except json.JSONDecodeError:
    print("Error: Response was not valid JSON.")
except Exception as e:
    print("Unexpected error:", e)
