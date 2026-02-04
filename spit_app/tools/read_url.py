import os
import json
import time
import math
import asyncio
from markdownify import markdownify as md
from playwright.async_api import async_playwright, TimeoutError
from bs4 import BeautifulSoup
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Read URL source page by page",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "A valid URL like 'https://example.com'."
                },
                "page": {
                    "type": "integer",
                    "description": "An integer from 1 to maximal page count for URL source."
                }
            },
            "required": ["url"]
        }
    }
}

PAGE_SIZE = 3000

PROMPT = "Use this function to access information on the internet."

PROMPT_INST = "Provide a valid URL beginning with http:// or https://. After requesting the URL, the function will give you the first page and the page count. After that you can request the individual pages with another call to this function with using the same URL. Each page is [page_size] characters long. Often, relevant data is not on the very first pages. Call this function again to search for the relevant data on the following pages."

SETTINGS = {
    "prompt": {"value": PROMPT, "stype": "text", "desc": "Prompt"},
    "page_size": {"value": PAGE_SIZE, "stype": "uinteger", "empty": False, "desc": "Page size (in characters)"}
}

class Validators:
    def page_size(value) -> bool:
        try:
            int(value)
        except:
            return False
        if int(value) < 500 or int(value) > 20000:
            return False
        return True

def file_name(app, url: str) -> str:
    file = url.replace("/", "_")
    file = file.replace(":", "-")
    directory = app.settings.path["cache"] / NAME
    directory.mkdir(parents=True, exist_ok=True)
    return directory / file

def maybe_load_cache(file: str) -> None|dict:
    if os.path.exists(file):
        with open(file, "r") as f:
            cache = json.loads(f.read())
        if cache["time"] + 3600 < time.time():
            return None
    else:
        return None
    return cache

async def load_page(url: str) -> None|dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(**p.devices["Desktop Chrome"])
        await context.add_init_script(
            "Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });"
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'vendor', { get: () => 'Google Inc.' });"
        )
        page = await context.new_page()
        try:
            await page.goto(url)
            await page.wait_for_load_state("networkidle", timeout=15_000)
        except:
            return None
        html = await page.content()
        await browser.close()
        soup = BeautifulSoup(html, 'html.parser')
        html = soup.select("h1, h2, h3, p, table")
        rethtml = '\n'.join([str(el) for el in html])
    return rethtml

def make_cache(html: str, file: str) -> dict:
    markdown = md(html)
    cache = {"time": time.time(), "markdown": markdown.strip()}
    with open(file, "w") as f:
        f.write(json.dumps(cache))
    return cache

def get_page(cache: dict, page: int) -> str:
    page_size = SETTINGS["page_size"]["value"]
    if len(cache["markdown"]) <= page_size:
        pages = 1
        page = 1
    else:
        pages = math.ceil(len(cache["markdown"]) / page_size)
    if page > pages:
        page = pages
    countl = page_size*(page-1)
    countr = page_size*page
    cont = ""
    if not page == pages:
        cont = f"\n\n[{NAME}]... continues on next page[/{NAME}]"
    return f"[{NAME}]Showing page {page} of {pages}[/{NAME}]\n\n"+cache["markdown"][countl:countr].strip()+cont

async def call(app, arguments: dict, chat_id: str):
    load_user_settings(app, NAME, SETTINGS)
    url = arguments["url"]
    if not url.startswith("http://") and not url.startswith("https://"):
        return "Invalid URL"
    page = 1
    if "page" in arguments:
        page = arguments["page"]
    file = file_name(app, url)
    cache = maybe_load_cache(file)
    if not cache:
        html = await load_page(url)
        if not html:
            return f"[{NAME}]Something went wrong! Please try again![/{NAME}]"
        cache = make_cache(html, file)
    if not cache["markdown"]:
        return f"[{NAME}]Something went wrong! Please try again![/{NAME}]"
    return get_page(cache, page)
