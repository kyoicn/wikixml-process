from typing import TypedDict, Optional, List, get_type_hints, Annotated
import json

class EventTime(TypedDict):
    time_str: Annotated[str, "String representation of time"]
    precision: Annotated[str, "year or month or day or hour or minute or second"]
    year: Annotated[Optional[int], "int or null"]
    month: Annotated[Optional[int], "int or null"]
    day: Annotated[Optional[int], "int or null"]
    hour: Annotated[Optional[int], "int or null"]
    minute: Annotated[Optional[int], "int or null"]
    second: Annotated[Optional[int], "int or null"]

class EventLocation(TypedDict):
    location_name: Annotated[str, "Name of location"]
    precision: Annotated[str, "spot or city or country or continent"]
    latitude: Annotated[Optional[float], "float or null"]
    longitude: Annotated[Optional[float], "float or null"]

class HistoricalEvent(TypedDict):
    event_title: Annotated[str, "Short title of the event"]
    event_description: Annotated[str, "Brief description"]
    start_time: EventTime  # No annotation = recurse
    end_time: Annotated[Optional[EventTime], "null or same structure as start_time (null if time spot)"]
    location: EventLocation  # No annotation = recurse

class WikiPage(TypedDict):
    title: str
    raw_content: str
    plain_text_content: str
    events: List[HistoricalEvent]
    link: str

def generate_schema(cls) -> dict:
    """
    Recursively generates a schema dictionary from a TypedDict class
    using Annotated metadata.
    """
    schema = {}
    type_hints = get_type_hints(cls, include_extras=True)
    
    for key, value in type_hints.items():
        # Check if it's annotated
        if hasattr(value, '__metadata__') and value.__metadata__:
            # Use the description string
            schema[key] = value.__metadata__[0]
        else:
            # If not annotated, check if it's a TypedDict and recurse
            # Unpack Optional/List types if necessary to find the underlying TypedDict
            # For this simple use case, we assume direct TypedDict or simple type
            if isinstance(value, type) and issubclass(value, dict):
                schema[key] = generate_schema(value)
            else:
                schema[key] = str(value)
                
    return schema

def get_event_schema_description() -> str:
    """
    Generates a JSON schema string derived from the TypedDict definitions
    to be used in the LLM prompt.
    """
    event_structure = generate_schema(HistoricalEvent)
    return json.dumps([event_structure], indent=2)
