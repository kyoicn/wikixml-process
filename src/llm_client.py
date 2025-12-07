import os
import json
import urllib.request
import urllib.error
import time

# Configuration from environment variables
OLLAMA_HOST = os.environ.get("OLLAMA_HOST")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL")

SYSTEM_PROMPT = (
    "You are a helpful assistant that converts Wikipedia Wikitext to clean, human-readable plain text. "
    "Remove all unnecessary templates, tags, annotations that are not for human reading. "
    "Only extract text content based on what exists in the input."
    "Only output the plain text content based on what you see."
    "You can use lightweight formatting for structured information, such as newlines and lists."
    "DO NOT add any additional information or content that is not present in the input."
)

MODEL_TEMPERATURE = 0.1  # Low temperature for deterministic cleaning
MODEL_NUM_PREDICT = -1   # Allow sufficient output

def clean_with_llm(text: str) -> str:
    """
    Sends the raw Wikitext to the Ollama LLM for cleaning.
    """
    if not text or not text.strip():
        return ""

    url = f"{OLLAMA_HOST}/api/generate"
    
    # Construct the prompt
    # Using raw prompt format. For chat models, using /api/chat might be better, 
    # but /api/generate works if the prompt is structured or if the model is flexible.
    full_prompt = f"{SYSTEM_PROMPT}\n\nInput Wikitext:\n{text}\n\nPlain Text Output:"

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": MODEL_TEMPERATURE,
            "num_predict": MODEL_NUM_PREDICT,
        }
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

    try:
        # Simple retry logic could be added here if needed, but keeping it simple for now.
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('response', '').strip()
            else:
                print(f"Error calling LLM: HTTP {response.status}")
                return text # Fallback to raw text on error? Or empty? simpler to return raw or partial.
                
    except urllib.error.URLError as e:
        print(f"Failed to connect to Ollama at {OLLAMA_HOST}: {e}")
        return text # Fallback
    except Exception as e:
        print(f"An error occurred during LLM processing: {e}")
        return text

if __name__ == "__main__":
    # Quick test
    sample = "'''Bold''' text and [[Link|Label]]."
    print(f"Original: {sample}")
    print(f"Cleaned: {clean_with_llm(sample)}")
