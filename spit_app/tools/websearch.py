import json
import asyncio
from ddgs import DDGS
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Search the web with duckduckgo.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The query for the search."
                }
            },
            "required": ["query"]
        }
    }
}

PROMPT = "Use this function to search the web."
MAX_RESULTS = 10
SAFESEARCH = "moderate"
PROMPT_INST = "You will get [max_results] results with links to follow the source. Safesearch is set to [save_search]."

SETTINGS = {
    "prompt": {"value": PROMPT, "stype": "text", "desc": "Prompt"},
    "max_results": {"value": MAX_RESULTS, "stype": "uinteger", "empty": False, "desc": "Number of results"},
    "safesearch": {"value": SAFESEARCH, "stype": "select_no_default", "empty": False,
                   "desc": "Save search", "options": ["on", "moderate", "off"]}
}

class Validators:
    def max_results(value) -> bool:
        try:
            int(value)
        except:
            return False
        if int(value) < 1 or int(value) > 100:
            return False
        return True

async def call(app, arguments: dict, chat_id: str):
    load_user_settings(app, NAME, SETTINGS)
    query = arguments["query"]
    safesearch = SETTINGS["safesearch"]["value"]
    max_results = SETTINGS["max_results"]["value"]
    try:
        results = await asyncio.to_thread(DDGS().text, query, safesearch=safesearch, max_results=max_results)
    except:
        return "No results found!"
    ret = "# Results"
    for result in results:
        ret += f"\n\n## {result['title']}\n\n- link: `{result['href']}`\n\n{result['body']}"
    return ret
