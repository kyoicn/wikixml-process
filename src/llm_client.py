import os
import json
import urllib.request
import urllib.error
from schema import get_event_schema_description
import time

# Configuration from environment variables
OLLAMA_HOST = os.environ.get("OLLAMA_HOST")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL")

PROMPT_CLEAN_TEXT = (
    "You are a helpful assistant that converts Wikipedia Wikitext to clean, human-readable plain text. "
    "Remove all unnecessary templates, tags, annotations that are not for human reading. "
    "Only extract text content based on what exists in the input. "
    "Only output the plain text content based on what you see. "
    "You can use lightweight formatting for structured information, such as newlines and lists. "
    "DO NOT add any additional information or content that is not present in the input. "
)

PROMPT_CLEAN_TEXT_ALT = (
    "The following is the raw content of a wikipedia data, which contains many annotations not for human readers. "
    "Help me convert it to a human-readable version by removing unnecessary annotations and other parts. "
    "The output should be plain text only with only minimum necessary formatting."
)

MODEL_TEMPERATURE_CLEAN_TEXT = 0.1  # Low temperature for fact-based extraction
MODEL_NUM_PREDICT_CLEAN_TEXT = -1   # Allow sufficient output

# Get the schema structure dynamically
EVENT_SCHEMA_JSON = get_event_schema_description()

PROMPT_EVENT_EXTRACTION = (
    "You are an expert document assistant. "
    "Your task is to find events mentioned or implied in the provided text, and extract them. "
    "Output a JSON list of objects. Each object should follow this structure:\n"
    f"{EVENT_SCHEMA_JSON}\n"
    "Not every event has all the information listed in the schema, so try your best to extract what you can. "
    "Some events are not explicitly mentioned in the text, but can be reliably inferred from the context, so you need to find those events as well based on your judgement. "
    "But only focus on what you can extract from the input text, don't guess or infer anything that is not present in the input."
    "Output ONLY the valid JSON list. If no events are found, return empty list []."
)

PROMPT_EVENT_EXTRACTION_ALT = (
    "# Role: Expert Event Extraction & Structuring Assistant\n"
    "## Objective\n"
    "Your task is to analyze the provided text, identify all events (both explicitly stated and strongly implied), and extract them into a strict JSON list format.\n"
    "## Input Source\n"
    "You will strictly use **only the provided text** as your source of truth. Do not use external knowledge to fill in missing details (e.g., do not infer coordinates for a known city, do not guess the year based on historical context).\n"
    "## JSON Output Schema\n"
    "You must output a JSON list of objects `[]`. Each object must adhere to this structure:\n\n"
    "```json\n"
    "{\n"
    "\"event_title\": \"Short title of the event (e.g., 'Birth of Roberto Gatti')\"\n",
    "\"event_description\": \"Brief description based on text\"\n",
    "\"start_time\": {\n"
    "    \"time_str\": \"Raw string representation from text (e.g., '20 October 1964')\",\n"
    "    \"precision\": \"One of: 'year', 'month', 'day', 'hour', 'minute', 'second', or null if unknown"",\n"
    "    \"year\": \"int or null\",\n"
    "    \"month\": \"int (1-12) or null\",\n"
    "    \"day\": \"int (1-31) or null\",\n"
    "    \"hour\": \"int (0-23) or null\",\n"
    "    \"minute\": \"int (0-59) or null\",\n"
    "    \"second\": \"int (0-59) or null\"\n"
    "},\n"
    "\"end_time\": \"null or same structure as start_time (use null if it is a specific time spot)\",\n"
    "\"location\": {\n"
        "\"location_name\": \"Name of location extracted from text\",\n"
        "\"precision\": \"One of: 'city', 'country', 'coordinates', or null\",\n"
        "\"latitude\": \"float or null (ONLY if present in text)\",\n"
        "\"longitude\": \"float or null (ONLY if present in text)\"\n"
    "}\n"
    "}\n"
    "Extraction Rules & Constraints\n"
    "1. Event Identification\n"
    "Explicit Events: Meetings, battles, ceremonies, movements.\n"
    "Implied Events: Lifecycle states (Birth, Death, Retirement, Foundation of a company).\n"
    "Example: \"Roberto Gatti (born 20 October 1964)\" -> Extract Event: \"Birth of Roberto Gatti\".\n"
    "No Events Found: If the text contains no events, output [].\n"
    "2. Time Handling (Strict)\n"
    "Absolute Dates: Extract years, months, and days into their respective integer fields.\n"
    "Relative Dates: If the text says \"two years later\" or \"the next day\", DO NOT calculate the date. Set the integer fields (year/month/day) to null. You may strictly keep the text phrase in time_str.\n"
    "Precision: Set the precision field based on the most granular integer field filled.\n"
    "3. Location Handling (Strict)\n"
    "Names: Extract city/country names into location_name.\n"
    "Coordinates: NEVER hallucinate or look up coordinates. If the text does not explicitly state \"lat 45.1, long 12.3\", then latitude and longitude must be null.\n"
    "4. Missing Information\n"
    "Do not guess. If a field (like location or end_time) is not mentioned or clearly implied, set it to null.\n"
    "Output Format\n"
    "Return ONLY the valid JSON list.\n"
    "Do not include markdown formatting (like json ... ) unless necessary for the interface, but prefer raw text.\n"
    "Do not add conversational text before or after the JSON.\n"
)

MODEL_TEMPERATURE_EVENT_EXTRACTION = 0.8
MODEL_NUM_PREDICT_EVENT_EXTRACTION = -1

def clean_with_llm(text: str) -> str:
    """
    Sends the raw Wikitext to the Ollama LLM for cleaning.
    """
    if not text or not text.strip():
        return ""

    url = f"{OLLAMA_HOST}/api/generate"
    
    # Construct the prompt
    full_prompt = f"{PROMPT_CLEAN_TEXT_ALT}\n\nInput Wikitext:\n{text}\n\nPlain Text Output:"

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": MODEL_TEMPERATURE_CLEAN_TEXT,
            "num_predict": MODEL_NUM_PREDICT_CLEAN_TEXT,
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
    
    full_prompt = f"{PROMPT_EVENT_EXTRACTION_ALT}\n\nInput Text:\n{text}\n\nJSON Output:"
    print(full_prompt)

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": full_prompt,
        "stream": False,
        "format": "json", # Force JSON mode if supported by Ollama/Model
        "options": {
            "temperature": MODEL_TEMPERATURE_EVENT_EXTRACTION,
            "num_predict": MODEL_NUM_PREDICT_EVENT_EXTRACTION
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
    print(f"Clean text prompt:\n{PROMPT_CLEAN_TEXT}\n")
    print(f"Event extraction prompt:\n{PROMPT_EVENT_EXTRACTION}\n")
