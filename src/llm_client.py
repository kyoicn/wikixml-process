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
    "Only extract text content based on what exists in the input. "
    "Only output the plain text content based on what you see. "
    "You can use lightweight formatting for structured information, such as newlines and lists. "
    "DO NOT add any additional information or content that is not present in the input. "
)

SYSTEM_PROMPT_ALT = (
    "The following is the raw content of a wikipedia data, which contains many annotations not for human readers. "
    "Help me convert it to a human-readable version by removing unnecessary annotations and other parts. "
    "The output should be plain text only with only minimum necessary formatting."
)

MODEL_TEMPERATURE = 0.1  # Low temperature for deterministic cleaning
MODEL_NUM_PREDICT = -1   # Allow sufficient output

EVENT_EXTRACTION_PROMPT = (
    "You are an expert historian assistant. Your task is to extract historical events from the provided text. "
    "Output a JSON list of objects. Each object should have the following structure:\n"
    "{\n"
    "  \"event_title\": \"Short title of the event\",\n"
    "  \"event_description\": \"Brief description\",\n"
    "  \"start_time\": {\n"
    "       \"time_str\": \"String representation of time\",\n"
    "       \"precision\": \"year/month/day/hour/minute/second\",\n"
    "       \"year\": int or null,\n"
    "       \"month\": int or null,\n"
    "       \"day\": int or null,\n"
    "       \"hour\": int or null,\n"
    "       \"minute\": int or null,\n"
    "       \"second\": int or null\n"
    "   },\n"
    "  \"end_time\": null or same structure as start_time (null if time spot),\n"
    "  \"location\": {\n"
    "       \"location_name\": \"Name of location\",\n"
    "       \"precision\": \"city/country/coordinates\",\n"
    "       \"latitude\": float or null,\n"
    "       \"longitude\": float or null\n"
    "   }\n"
    "}\n"
    "Output ONLY the valid JSON list. If no events are found, return empty list []."
)

def clean_with_llm(text: str) -> str:
    """
    Sends the raw Wikitext to the Ollama LLM for cleaning.
    """
    if not text or not text.strip():
        return ""

    url = f"{OLLAMA_HOST}/api/generate"
    
    # Construct the prompt
    full_prompt = f"{SYSTEM_PROMPT_ALT}\n\nInput Wikitext:\n{text}\n\nPlain Text Output:"

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": MODEL_TEMPERATURE,
            "num_predict": MODEL_NUM_PREDICT,
        }
    }

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('response', '').strip()
            else:
                print(f"Error calling LLM: HTTP {response.status}")
                return text
                
    except Exception as e:
        print(f"An error occurred during LLM processing: {e}")
        return text

def extract_events_with_llm(text: str) -> list:
    """
    Extracts historical events from the plain text using LLM.
    Returns a list of event dictionaries.
    """
    if not text or not text.strip():
        return []

    url = f"{OLLAMA_HOST}/api/generate"
    
    full_prompt = f"{EVENT_EXTRACTION_PROMPT}\n\nInput Text:\n{text}\n\nJSON Output:"

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": full_prompt,
        "stream": False,
        "format": "json", # Force JSON mode if supported by Ollama/Model
        "options": {
            "temperature": 0.1,
            "num_predict": -1
        }
    }

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                result = json.loads(response.read().decode('utf-8'))
                response_text = result.get('response', '').strip()
                
                # Attempt to parse JSON
                try:
                    # Sometimes models wrap in ```json ... ```
                    if "```json" in response_text:
                        response_text = response_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in response_text:
                        response_text = response_text.split("```")[1].strip()
                        
                    events = json.loads(response_text)
                    if isinstance(events, list):
                        return events
                    return []
                except json.JSONDecodeError:
                    print(f"Failed to parse JSON from LLM event extraction: {response_text[:50]}...")
                    return []
            else:
                print(f"Error calling LLM for events: HTTP {response.status}")
                return []
                
    except Exception as e:
        print(f"An error occurred during LLM event extraction: {e}")
        return []

if __name__ == "__main__":
    # Quick test
    sample = "'''Bold''' text and [[Link|Label]]."
    print(f"Original: {sample}")
    print(f"Cleaned: {clean_with_llm(sample)}")
