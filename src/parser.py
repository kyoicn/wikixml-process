import xml.etree.ElementTree as ET
import urllib.parse
from typing import TypedDict, Generator

class WikiPage(TypedDict):
    title: str
    raw_content: str
    plain_text_content: str
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
    # Although wikipedia handles many chars, safe encoding is good practice, 
    # but standard requirement is usually just space->underscore for basic links.
    # We will percent-encode to be safe for a valid URL.
    # safe_title = urllib.parse.quote(safe_title) # Optional: user might want raw readable links, but standard is encoded.
    # Let's stick to simple replacement for now as it's more human readable in JSON, 
    # unless special chars demand encoding. Wikipedia usually redirects well.
    # Actually, let's just do space -> underscore as requested implicitly by standard wiki format.
    return f"https://en.wikipedia.org/wiki/{safe_title}"

from llm_client import clean_with_llm

def process_xml(file_path: str) -> Generator[WikiPage, None, None]:
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
            
            for child in elem:
                child_tag = get_tag_name(child)
                if child_tag == 'title':
                    title = child.text
                elif child_tag == 'revision':
                    for rev_child in child:
                        if get_tag_name(rev_child) == 'text':
                            text_content = rev_child.text
                            break
            
            if title:
                raw_content = text_content or ""
                yield {
                    'title': title,
                    'raw_content': raw_content,
                    'plain_text_content': clean_with_llm(raw_content),
                    'link': construct_wiki_url(title)
                }
            
            # Clear the element to save memory
            elem.clear()
