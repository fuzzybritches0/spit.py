# SPDX-License-Identifier: GPL-2.0
import os
import json
import time
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Fetch and read the content of a URL. Handles JavaScript-rendered pages.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "A valid URL like 'https://example.com'."
                },
                "max_length": {
                    "type": "integer",
                    "description": "Maximum characters to return. Default 5000."
                }
            },
            "required": ["url"]
        }
    }
}

MAX_LENGTH = 5000
CACHE_TTL = 3600
TIMEOUT = 15_000

PROMPT = "Use this function to access information on the internet."
PROMPT_INST = "Provide a valid URL beginning with http:// or https://. The function will return plain text content from the page, up to [max_length] characters."

SETTINGS = {
    "prompt": {"value": PROMPT, "stype": "text", "desc": "Prompt"},
    "max_length": {"value": MAX_LENGTH, "stype": "uinteger", "empty": False, "desc": "Maximum content length (characters)"}
}

class Validators:
    def max_length(value) -> bool:
        try:
            int(value)
        except:
            return (False, None)
        if int(value) < 500 or int(value) > 20000:
            return (False, "Value out of range")
        return (True, None)

def file_name(app, url: str) -> str:
    safe_url = "".join(c if c.isalnum() or c in "-._~" else "_" for c in url)
    directory = app.settings.path["cache"] / NAME
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{safe_url}.json"

def maybe_load_cache(cache_path: str) -> dict | None:
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r") as f:
                cache = json.load(f)
            if time.time() - cache["time"] < CACHE_TTL:
                return cache
        except Exception:
            pass
    return None

def save_cache(cache: dict, cache_path: str) -> None:
    with open(cache_path, "w") as f:
        json.dump(cache, f)

async def fetch_url(url: str) -> str | None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US,en",
        )
        page = await context.new_page()
        # Inject scripts before page loads to override bot detection
        await page.add_init_script("""
            // Override webdriver flag
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    { description: "PDF Viewer", filename: "internal-pdf-viewer" },
                    { description: "Chrome PDF Viewer", filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai" }
                ]
            });

            // Override languages
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });

            // Override chrome object
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };

            // Remove automation flags
            delete document.documentElement.getAttribute('data-puppeteer');
            delete document.documentElement.getAttribute('data-selenium');
        """)

        try:
            # Navigate to URL - wait for DOM content first, then network idle
            await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)

            # Wait for all network activity to settle (dynamic content loading)
            await page.wait_for_load_state("networkidle", timeout=15_000)

            # Additional wait for JavaScript rendering
            await page.wait_for_timeout(3000)

            # Try to scroll down to trigger lazy-loaded content
            try:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1000)
            except:
                pass
            html = await page.content()
        except PlaywrightTimeout:
            await browser.close()
            return "ERROR: Timeout waiting for page to load"
        except Exception as e:
            await browser.close()
            return f"ERROR: {type(e).__name__}: {e}"
        finally:
            await browser.close()

        return html


def extract_text(html: str, max_length: int) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    html = soup.select("h1, h2, h3, h4, p, li, pre, blockquote, table")
    text_parts = []
    total_length = 0
    for el in html:
        text = str(el)
        if not text:
            continue
        text_parts.append(text)
        total_length += len(text)
        if total_length >= max_length:
            break
    result = '\n\n'.join(text_parts)
    if len(result) > max_length:
        result = result[:max_length - 50].rstrip() + "\n\n[Content truncated...]"
    return result.strip()

async def call(app, arguments: dict, chat_id: str) -> str:
    load_user_settings(app, NAME, SETTINGS)
    url = arguments["url"]
    max_length = SETTINGS["max_length"]["value"]
    if not url.startswith("http://") and not url.startswith("https://"):
        return "ERROR: Invalid URL. Must begin with http:// or https://"
    cache_path = file_name(app, url)
    cache = maybe_load_cache(cache_path)
    if cache and "content" in cache:
        return "```html\n" + cache["content"] + "\n```"
    html = await fetch_url(url)
    if html is None or isinstance(html, str) and html.startswith("ERROR:"):
        return html
    content = extract_text(html, max_length)
    if not content:
        return "ERROR: No readable content found on this page."
    cache = {"time": time.time(), "content": content}
    save_cache(cache, cache_path)
    return "```html\n" + content + "\n```"
