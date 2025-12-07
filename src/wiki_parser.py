import xml.etree.ElementTree as ET
import urllib.parse
from typing import TypedDict, Generator, Optional, Callable, List
from llm_client import clean_with_llm, extract_events_with_llm

class EventTime(TypedDict):
    time_str: str
    precision: str
    year: Optional[int]
    month: Optional[int]
    day: Optional[int]
    hour: Optional[int]
    minute: Optional[int]
    second: Optional[int]

class EventLocation(TypedDict):
    location_name: str
    precision: str
    latitude: Optional[float]
    longitude: Optional[float]

class HistoricalEvent(TypedDict):
    event_title: str
    event_description: str
    start_time: EventTime
    end_time: Optional[EventTime]
    location: EventLocation

class WikiPage(TypedDict):
    title: str
    raw_content: str
    plain_text_content: str
    events: List[HistoricalEvent]
    link: str

def get_tag_name(element):
    """
    Extracts the tag name without having to hardcode the namespace.
    E.g. {http://www.mediawiki.org/xml/export-0.11/}page -> page
    """
    if '}' in element.tag:
        return element.tag.split('}', 1)[1]
    return element.tag

def construct_wiki_url(title):
    """
    Constructs a Wikipedia URL from the page title.
    Replaces spaces with underscores.
    """
    safe_title = title.replace(' ', '_')
    return f"https://en.wikipedia.org/wiki/{safe_title}"

def process_xml(file_path: str, status_callback: Optional[Callable[[dict], None]] = None) -> Generator[WikiPage, None, None]:
    """
    Iteratively parses the XML file yielding dictionaries of extracted data.
    """
    # Namespaces can be tricky, so we'll strip them or handle them generically.
    # We are looking for 'page' elements.
    
    context = ET.iterparse(file_path, events=('end',))
    
    for event, elem in context:
        tag = get_tag_name(elem)
        
        if tag == 'page':
            # Initialize data placeholders
            title = None
            text_content = None
            
            # Since we are at the 'end' of the page element, 
            # we can traverse its children locally or look at what we've built.
            # However, simpler to look at children directly if file isn't massive within a single page node.
            # Standard wikipedia pages aren't RAM-breakingly huge usually.
            
            # We need to find the title first for the callback if we want to be precise,
            # but element children order might vary. Usually title is first.
            # Let's iterate and extract.
            
            for child in elem:
                child_tag = get_tag_name(child)
                if child_tag == 'title':
                    title = child.text
                    if status_callback and title:
                        status_callback({"stage": "start", "title": title})
                elif child_tag == 'revision':
                    for rev_child in child:
                        if get_tag_name(rev_child) == 'text':
                            text_content = rev_child.text
                            if status_callback and text_content and title:
                                status_callback({"stage": "content", "title": title, "len": len(text_content)})
                            break
            
            if title:
                raw_content = text_content or ""
                if status_callback:
                    status_callback({"stage": "llm", "title": title})
                
                plain_text = clean_with_llm(raw_content)
                
                # Extract events
                if status_callback:
                    status_callback({"stage": "events", "title": title})
                    
                events = extract_events_with_llm(plain_text)
                # DEBUG PRINT
                import sys
                print(f"Extracting events for {title}, count: {len(events)}", file=sys.stderr)
                
                if status_callback:
                    status_callback({"stage": "events_done", "title": title, "count": len(events)})
                
                yield {
                    'title': title,
                    'raw_content': raw_content,
                    'plain_text_content': plain_text,
                    'events': events,
                    'link': construct_wiki_url(title)
                }
            
            # Clear the element to save memory
            elem.clear()
