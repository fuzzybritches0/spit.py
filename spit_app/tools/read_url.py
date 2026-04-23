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
                }
            },
            "required": ["url"]
        }
    }
}

CACHE_TTL = 0
TIMEOUT = 30_000

PROMPT = "Use this function to access information on the internet."
PROMPT_INST = "Provide a valid URL beginning with http:// or https://. The function will return plain text content from the page."

SETTINGS = {
    "prompt": {"value": PROMPT, "stype": "text", "desc": "Prompt"},
    "cache_ttl": {"value": CACHE_TTL, "stype": "uinteger", "empty": False, "desc": "Cache TTL (minutes) (0 - don't cache URLs)"}
}

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
            if time.time() - cache["time"] < SETTINGS["cache_ttl"]["value"]:
                return cache
        except Exception:
            pass
    return None

def save_cache(cache: dict, cache_path: str) -> None:
    with open(cache_path, "w") as f:
        json.dump(cache, f)

async def fetch_url(url: str) -> str | None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding'
            ]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US,en",
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False,
            # Ignore HTTPS errors (for testing)
            # ignore_https_errors=True,
        )
        page = await context.new_page()
        await page.add_init_script("""
        (function() {
            'use strict';

            // ========== 1. NAVIGATOR PROPERTIES ==========

            // Webdriver flag
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
                configurable: true
            });

            // Permissions (prompt instead of denied)
            const originalQuery = window.origNavigator.permissions ?
                window.origNavigator.permissions.query :
                Navigator.prototype.permissions?.query;

            if (originalQuery) {
                Permissions.prototype.query = function(query) {
                    if (query.name === 'notifications') {
                        return Promise.resolve({ state: 'prompt', onchange: null });
                    }
                    if (query.name === 'geolocation') {
                        return Promise.resolve({ state: 'prompt', onchange: null });
                    }
                    return originalQuery.apply(this, arguments);
                };
            }

            // ========== 2. CHROME OBJECT ==========
            Object.defineProperty(window, 'chrome', {
                get: function() {
                    return {
                        runtime: {},
                        loadsExtensionContent: false,
                        app: {},
                        instanceID: function() { return Promise.resolve('instance_id'); },
                        getManifest: function() { return { manifest_version: 3 }; },
                        getPlatformInfo: function() {
                            return Promise.resolve({
                                os: 'POSIX',
                                arch: 'x86_64',
                                naclArch: 'x86-64',
                                arch: 'x86_64'
                            });
                        },
                        runtime: {
                            connect: function() { return { onMessage: { addListener: function() {} }, postMessage: function() {} }; },
                            sendMessage: function() { return Promise.resolve({}); },
                            onMessage: { addListener: function() {} },
                            onConnect: { addListener: function() {} }
                        }
                    };
                },
                configurable: true,
                enumerable: true
            });

            // ========== 3. CANVAS FINGERPRINT PROTECTION ==========
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function(...args) {
                const ctx = this.getContext('2d');
                if (ctx) {
                    try {
                        const imageData = ctx.getImageData(0, 0, this.width, this.height);
                        // Add subtle noise to defeat fingerprinting
                        for (let i = 0; i < imageData.data.length; i += 4) {
                            imageData.data[i] = (imageData.data[i] + Math.floor(Math.random() * 3) - 1 + 256) % 256;
                            imageData.data[i + 1] = (imageData.data[i + 1] + Math.floor(Math.random() * 3) - 1 + 256) % 256;
                            imageData.data[i + 2] = (imageData.data[i + 2] + Math.floor(Math.random() * 3) - 1 + 256) % 256;
                        }
                        ctx.putImageData(imageData, 0, 0);
                    } catch (e) {
                        // Context might be tainted, ignore
                    }
                }
                return originalToDataURL.apply(this, args);
            };

            // Also override toBlob
            const originalToBlob = HTMLCanvasElement.prototype.toBlob;
            if (originalToBlob) {
                HTMLCanvasElement.prototype.toBlob = function(...args) {
                    const ctx = this.getContext('2d');
                    if (ctx) {
                        try {
                            const imageData = ctx.getImageData(0, 0, this.width, this.height);
                            for (let i = 0; i < imageData.data.length; i += 4) {
                                imageData.data[i] = (imageData.data[i] + Math.floor(Math.random() * 3) - 1 + 256) % 256;
                                imageData.data[i + 1] = (imageData.data[i + 1] + Math.floor(Math.random() * 3) - 1 + 256) % 256;
                                imageData.data[i + 2] = (imageData.data[i + 2] + Math.floor(Math.random() * 3) - 1 + 256) % 256;
                            }
                            ctx.putImageData(imageData, 0, 0);
                        } catch (e) {
                            // Ignore
                        }
                    }
                    return originalToBlob.apply(this, args);
                };
            }

            // ========== 4. WEBGL FINGERPRINT PROTECTION ==========
            const getParameterOriginal = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(param) {
                // Return realistic values for known fingerprinting params
                if (param === 37445) return 'Intel Open Source Technology Center'; // UNMASKED_VENDOR
                if (param === 37446) return 'Mesa DRI Intel(R) HD Graphics (KBL GT2)'; // UNMASKED_RENDERER
                if (param === 7936) return 'WebGL 1.0'; // VERSION
                if (param === 7937) return 'WebGL GLSL 1.0'; // SHADING_LANGUAGE_VERSION
                return getParameterOriginal.apply(this, arguments);
            };

            // Override getExtension
            const getExtensionOriginal = WebGLRenderingContext.prototype.getExtension;
            WebGLRenderingContext.prototype.getExtension = function(name) {
                const ext = getExtensionOriginal.call(this, name);
                if (!ext) return null;
                return ext;
            };

            // ========== 5. AUDIO FINGERPRINT PROTECTION ==========
            const audioContextOriginal = window.OfflineAudioContext || window.webkitOfflineAudioContext;
            if (audioContextOriginal) {
                const OffscreenAudioContext = window.OfflineAudioContext;

                window.OfflineAudioContext = function(...args) {
                    const context = new OffscreenAudioContext(...args);
                    const originalGetChannelData = context.getChannelData;
                    context.getChannelData = function(channel) {
                        const data = originalGetChannelData.call(this, channel);
                        // Add subtle noise
                        for (let i = 0; i < data.length; i++) {
                            data[i] += (Math.random() - 0.5) * 0.000001;
                        }
                        return data;
                    };
                    return context;
                };
                window.OfflineAudioContext.prototype = OffscreenAudioContext.prototype;
            }

            // ========== 6. AUTOMATION ATTRIBUTE CLEANUP ==========
            // Override getAttribute to filter automation-specific attributes
            const originalGetAttribute = Element.prototype.getAttribute;
            Element.prototype.getAttribute = function(name, ...args) {
                if (name === 'data-puppeteer-element-check' ||
                    name === 'data-puppeteer-page-id' ||
                    name === 'data-webdriver' ||
                    name === 'puppeteer-script-id' ||
                    name === 'data-selenium' ||
                    name === 'data-hypernova' ||
                    name === '__webdriver_element') {
                    return null;
                }
                return originalGetAttribute.call(this, name, ...args);
            };

            // Also override document.documentElement.getAttribute
            const originalDocGetAttribute = document.documentElement?.getAttribute?.bind(document.documentElement);
            if (originalDocGetAttribute) {
                document.documentElement.getAttribute = function(name, ...args) {
                    if (name === 'data-puppeteer-page-id' ||
                        name === 'puppeteer-execution-context-id' ||
                        name.startsWith('data-puppeteer-') ||
                        name.startsWith('data-webdriver')) {
                        return null;
                    }
                    return originalDocGetAttribute(name, ...args);
                };
            }

            // ========== 7. CONSOLE POLLING PROTECTION ==========
            // Some sites poll console for automation messages
            const originalConsoleDebug = console.debug;
            console.debug = function(...args) {
                const msg = args.join(' ').toLowerCase();
                if (msg.includes('puppeteer') ||
                    msg.includes('playwright') ||
                    msg.includes('webdriver') ||
                    msg.includes('selenium')) {
                    return;
                }
                return originalConsoleDebug.apply(console, args);
            };

            const originalConsoleError = console.error;
            console.error = function(...args) {
                const msg = args.join(' ').toLowerCase();
                if (msg.includes('puppeteer') ||
                    msg.includes('playwright') ||
                    msg.includes('webdriver') ||
                    msg.includes('automation')) {
                    return;
                }
                return originalConsoleError.apply(console, args);
            };

            // ========== 8. LANGUAGES SPOOFING ==========
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
                enumerable: true,
                configurable: true
            });

            // ========== 9. PLUGINS SPOOFING ==========
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    // Return a realistic plugin list
                    const plugins = [
                        { name: 'Chrome PDF Plugin', description: 'Portable Document Format', suffixes: 'pdf' },
                        { name: 'Chrome PDF Viewer', description: '', suffixes: '' },
                        { name: 'Native Client', description: '', suffixes: '' }
                    ];
                    plugins.length = 3;
                    plugins.__proto__ = PluginArray.prototype;
                    return plugins;
                },
                enumerable: true,
                configurable: true
            });

            // ========== 10. HARDWARE CONCURRENCY / DEVICE MEMORY ==========
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8,
                configurable: true
            });

            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8,
                configurable: true
            });

            // ========== 11. KEYBOARD/MOUSE EVENTS ==========
            // Ensure keyboard appears functional
            if (!Object.getOwnPropertyDescriptor(Keyboard.prototype, 'onkeydown')) {
                Object.defineProperty(Keyboard.prototype, 'onkeydown', { get: () => null, set: () => {} });
            }

            // ========== 12. IFRAMES DETECTION ==========
            // Some scripts check for iframes in unusual places
            Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
                get: function() {
                    try {
                        return window.frames[this.id] || {};
                    } catch (e) {
                        return {};
                    }
                }
            });

            // ========== 13. ELEMENT PROPERTIES ==========
            // Defeat hidden element detection
            Object.defineProperties(Element.prototype, {
                offsetParent: { get: function() { return this.parentElement; } },
                offsetTop: { get: function() { return 0; } },
                offsetLeft: { get: function() { return 0; } },
                offsetWidth: { get: function() { return this.width || 0; } },
                offsetHeight: { get: function() { return this.height || 0; } }
            });

            // ========== 14. SCREEN PROPERTIES ==========
            Object.defineProperty(screen, 'availWidth', { get: () => 1280 });
            Object.defineProperty(screen, 'availHeight', { get: () => 720 });
            Object.defineProperty(screen, 'width', { get: () => 1280 });
            Object.defineProperty(screen, 'height', { get: () => 800 });
            Object.defineProperty(screen, 'colorDepth', { get: () => 24 });
            Object.defineProperty(screen, 'pixelDepth', { get: () => 24 });

            // ========== 15. VENDOR / PRODUCT ==========
            Object.defineProperty(navigator, 'vendor', {
                get: () => 'Google Inc.',
                configurable: true
            });

            // ========== 16. MATH OBJECT FINGERPRINTING ==========
            // Some sites use Math operations to detect automation
            const originalMathRandom = Math.random;
            Math.random = function() {
                return originalMathRandom();
            };

            // ========== 17. DATE OBJECT (prevent frozen time) ==========
            const DateOriginal = Date;
            window.Date = function(...args) {
                const date = args.length ? new DateOriginal(...args) : new DateOriginal();
                return date;
            };
            window.Date.prototype = DateOriginal.prototype;
            window.Date.now = DateOriginal.now;

            // ========== 18. PERFORMANCE API ==========
            const originalNow = performance.now;
            if (originalNow) {
                Object.defineProperty(performance, 'now', {
                    get: () => {
                        return function() {
                            return originalNow.apply(performance, arguments);
                        };
                    }()
                });
            }

            // ========== 19. OUTER DIMENSIONS (Chrome 110+) ==========
            // Some checks use window.outerWidth/Height vs inner
            Object.defineProperty(window, 'outerWidth', { get: () => 1280 });
            Object.defineProperty(window, 'outerHeight', { get: () => 800 });
            Object.defineProperty(window, 'innerWidth', { get: () => 1181 });
            Object.defineProperty(window, 'innerHeight', { get: () => 600 });

            // ========== 20. REMOVE AUTOMATION FLAGS ==========
            delete window._Selenium_IDE_Recorder;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;

        })();
        """)
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
            await page.wait_for_timeout(5000)
            try:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1000)
                await page.evaluate("window.scrollTo(0, 0)")
            except:
                pass
            html = await page.content()
        except PlaywrightTimeout:
            return "ERROR: Timeout waiting for page to load"
        except Exception as e:
            return f"ERROR: {type(e).__name__}: {e}"
        finally:
            await browser.close()
        return html

def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    html = soup.select("h1, h2, h3, h4, p, li, pre, blockquote, table")
    text_parts = []
    for el in html:
        text = str(el)
        if not text:
            continue
        text_parts.append(text)
    result = '\n\n'.join(text_parts)
    return result.strip()

async def call(app, arguments: dict, chat_id: str) -> str:
    load_user_settings(app, NAME, SETTINGS)
    url = arguments["url"]
    if not url.startswith("http://") and not url.startswith("https://"):
        return "ERROR: Invalid URL. Must begin with http:// or https://"
    cache_path = file_name(app, url)
    cache = maybe_load_cache(cache_path)
    if cache and "html" in cache:
        html = cache["html"]
    else:
        html = await fetch_url(url)
        if html is None:
            return "ERROR: No data received!"
        elif isinstance(html, str) and html.startswith("ERROR:"):
            return html
        cache = {"time": time.time(), "html": html}
        save_cache(cache, cache_path)
    content = extract_text(html)
    if not content:
        return "ERROR: No readable content found on this page."
    return "```html\n" + content + "\n```"
