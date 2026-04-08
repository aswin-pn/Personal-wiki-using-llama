import requests
from src.config import OLLAMA_API, MODEL_NAME

def query_ollama(prompt, stream=False):
    """Handles communication with the local Ollama instance."""
    try:
        response = requests.post(OLLAMA_API, json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": stream
        })
        if response.status_code == 200:
            return response.json().get("response", "").strip()
        else:
            return f"Error: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Connection error: Could not connect to local Ollama API."
