# WikiXML Process

Process Wikipedia XML dumps to extract page data into JSON format.

## specialized Schema

The output is a JSON array of objects. Each object represents a single Wikipedia page.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `title` | `string` | The title of the Wikipedia page. |
| `raw_content` | `string` | The raw wikitext content of the page's latest revision. |
| `plain_text_content` | `string` | A cleaned, human-readable version of the content (experimental). |
| `link` | `string` | The constructed URL for the page on en.wikipedia.org. |

### Example

```json
[
  {
    "title": "Roberto Gatti",
    "raw_content": "{{short description|Italian footballer}}...",
    "plain_text_content": "Roberto Gatti (born 20 October 1964) is a retired Italian football defender...",
    "link": "https://en.wikipedia.org/wiki/Roberto_Gatti"
  }
]
```