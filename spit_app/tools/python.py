# SPDX-License-Identifier: GPL-2.0
import multiprocessing
import sys
import traceback
import os
import builtins
import importlib
import threading
import asyncio
import queue
from spit_app.tool_call import load_user_settings

NAME = __file__.split("/")[-1][:-3]

DESC = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": "Run a Python script in a sandbox.",
        "parameters": {
            "type": "object",
            "properties": {
                "script": {
                    "type": "string",
                    "description": "A Python script to execute in the sandbox."
                }
            },
            "required": ["script"]
        }
    }
}

MAX_SECONDS = 10
MAX_MEMORY_MB = 100
MODULES = "math, random, json, re, datetime, time, itertools, functools, operator, collections, heapq, bisect, enum, typing, string, numbers, pprint, copy, uuid, base64, binascii, csv, struct, textwrap, urllib.parse"
BUILTINS = "abs, all, any, bool, bytes, chr, complex, dict, divmod, enumerate, filter, float, frozenset, hash, int, isinstance, issubclass, iter, len, list, map, max, min, next, object, ord, pow, print, range, repr, reversed, round, set, slice, sorted, str, sum, tuple, type, zip, __build_class__, property, staticmethod, classmethod, BaseException, Exception, RuntimeError, ValueError"
PROMPT = "Among other things, you can use this function to aid your reasoning, write proofs, or avoid arithmetic mistakes."
PROMPT_INST= "You can import the following modules: [modules].\nYou are restricted to the following builtins: [builtins].\nYour script may run for [timeout] seconds.\nYour script may not exceed [max_mem_mb] MB of memory usage."

SETTINGS = {
    "prompt": { "value": PROMPT, "stype": "text", "desc": "Prompt" },
    "timeout": { "value": MAX_SECONDS, "stype": "uinteger", "empty": False, "desc": "Timeout" },
    "max_mem_mb": { "value": MAX_MEMORY_MB, "stype": "uinteger", "empty": False,
                   "desc": "Maximum Memory Usage (MB)" },
    "modules": { "value": MODULES, "stype": "text", "desc": "Allowed Importable Modules" },
    "builtins": { "value": BUILTINS, "stype": "text", "desc": "Allowed Builtins" }
}

_MODULES = []
_BUILTINS = {}

def _refresh_whitelists_from_settings() -> None:
    _modules = SETTINGS["modules"]["value"]
    _modules = _modules.split(",")
    for module in _modules:
        _MODULES.append(module.strip())

    _builtins = SETTINGS["builtins"]["value"]
    _builtins = _builtins.split(",")
    for builtin in _builtins:
        builtin = builtin.strip()
        if builtin:
            _BUILTINS[builtin] = getattr(builtins, builtin)
    _BUILTINS["__import__"] = _whitelisted_import

def _whitelisted_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name not in _MODULES and name.split(".")[0] not in _MODULES:
        raise ImportError(f"Import of '{name}' not permitted.")
    return builtins.__import__(name, globals, locals, fromlist, level)

class _streaming_writer:
    def __init__(self, conn, stream_type: str):
        self.conn = conn
        self.type = stream_type
        self.buffer = ""

    def write(self, data):
        if not data:
            return
        self.buffer += data
        self.flush()

    def flush(self):
        if self.buffer:
            self.conn.send({"type": self.type, "data": self.buffer})
            self.buffer = ""

def _worker(code: str, conn):
    sys.stdout = _streaming_writer(conn, "stdout")
    sys.stderr = _streaming_writer(conn, "stderr")
    try:
        try:
            import resource
            mem_bytes = SETTINGS["max_mem_mb"]["value"] * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        except Exception:
            pass

        exec(code, {"__builtins__": _BUILTINS, "__name__": "__main__"}, {})
    except Exception as exc:
        lineno = 0
        tbframes = traceback.extract_tb(exc.__traceback__)
        for tbframe in tbframes:
            if tbframe.filename in ("<string>", "<stdin>"):
                lineno = tbframe.lineno
        formatted = f"\n{type(exc).__name__}: {exc}"
        if lineno > 0:
            formatted = f"\nLine {lineno}: {type(exc).__name__}: {exc}"
        conn.send({"type": "exception", "data": f"ERROR: {formatted}"})
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        conn.close()

async def call_async_generator(app, arguments: dict, chat_id):
    load_user_settings(app, NAME, SETTINGS)
    _refresh_whitelists_from_settings()

    parent_conn, child_conn = multiprocessing.Pipe(duplex=False)

    proc = multiprocessing.Process(
        target=_worker, args=(arguments["script"], child_conn), daemon=True
    )
    proc.start()

    q = asyncio.Queue()

    def _pump():
        try:
            while True:
                if not parent_conn.poll(0.1):
                    if not proc.is_alive():
                        break
                    continue
                msg = parent_conn.recv()
                asyncio.run_coroutine_threadsafe(q.put(msg), loop)
        finally:
            asyncio.run_coroutine_threadsafe(q.put(None), loop)

    loop = asyncio.get_event_loop()
    pump_thread = threading.Thread(target=_pump, daemon=True)
    pump_thread.start()

    timeout = SETTINGS["timeout"]["value"]
    start = loop.time()

    while True:
        remaining = timeout - (loop.time() - start)
        try:
            msg = await asyncio.wait_for(q.get(), timeout=remaining)
        except asyncio.TimeoutError:
            if proc.is_alive():
                proc.terminate()
                proc.join()
            yield f"\nTimeoutError: execution exceeded {timeout}s\n"
            break

        if msg is None:
            break

        yield msg["data"]

    if proc.is_alive():
        proc.terminate()
        proc.join()
    pump_thread.join(timeout=0.1)
