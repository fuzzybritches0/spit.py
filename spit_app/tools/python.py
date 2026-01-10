# SPDX-License-Identifier: GPL-2.0
import multiprocessing
import sys
import traceback
import os
import builtins
import importlib
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

def _worker(code: str, conn):
    from io import StringIO
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = out_buf = StringIO()
    sys.stderr = err_buf = StringIO()

    try:
        try:
            import resource
            mem_bytes = SETTINGS["max_memory_mb"]["value"] * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        except Exception:
            pass

        exec(code, {"__builtins__": _BUILTINS, "__name__": "__main__"}, {})
        exc = None
    except Exception as error:
        exc = f"\n{type(error).__name__}: {error}\n"
    finally:
        conn.send({
            "stdout": out_buf.getvalue(),
            "stderr": err_buf.getvalue(),
            "exception": exc,
        })
        conn.close()
        sys.stdout, sys.stderr = old_out, old_err

def run_sandboxed(code: str) -> dict:
    parent_conn, child_conn = multiprocessing.Pipe(duplex=False)
    proc = multiprocessing.Process(target=_worker, args=(code, child_conn))
    proc.start()
    proc.join(SETTINGS["timeout"]["value"])

    if proc.is_alive():
        proc.terminate()
        proc.join()
        return {
            "stdout": "",
            "stderr": "",
            "exception": f"\nTimeoutError: execution exceeded {SETTINGS['timeout']['value']}s\n",
        }

    if parent_conn.poll():
        return parent_conn.recv()
    else:
        return {
            "stdout": "",
            "stderr": "",
            "exception": "\nUnknown error: child did not send data\n",
        }

def call(app, arguments: dict, chat_id) -> str:
    load_user_settings(app, NAME, SETTINGS)
    _refresh_whitelists_from_settings()
    res = run_sandboxed(arguments["script"])
    parts = []
    if res["stdout"]:
        parts.append(res["stdout"])
    if res["stderr"]:
        parts.append(res["stderr"])
    if res["exception"]:
        parts.append(res["exception"])
    return "```\n" + "\n".join(parts) + "\n```"
