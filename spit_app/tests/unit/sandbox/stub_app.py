#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""A stub app and a helper that runs a script through a real Run.

CommonMixIn and Run ask the app for exactly three things -- two lookups and the
sandbox paths -- so they can be driven without Textual, which is not a dependency
of the tests and is not installed everywhere they run. sandbox=False keeps bwrap
out of the way: the file delivery, the stream handling and the process group are
the same either way, and outside bwrap the process table is honest -- nothing
tears down the sandbox on the parent's exit, so what leaks leaks visibly.
"""
import asyncio
import os
import time
from pathlib import Path


class StubChat:
    def cs(self, key):
        return "unittest"

    def watchdog(self, proc, run):
        pass


class StubMain:
    def __init__(self, chat):
        self.chat = chat

    def query_one(self, selector):
        return self.chat


class StubApp:
    def __init__(self, sandbox_root, tmp_root):
        self.settings = type("S", (), {"path": {"sandbox": Path(sandbox_root),
                                                "sandbox_tmp": Path(tmp_root)}})
        self.chat = StubChat()

    def query_one(self, selector):
        return StubMain(self.chat)


def run_as_file(script: str, home: str, root: str, timeout: int = 0):
    """Run a script through Run with file delivery. Returns (output, leftovers, seconds)."""
    from spit_app.tools.run.run import Run

    sandbox_root = os.path.join(root, "home")
    tmp_root = os.path.join(root, "tmp")
    os.makedirs(sandbox_root, exist_ok=True)
    os.makedirs(tmp_root, exist_ok=True)
    saved_home = os.environ.get("HOME")
    os.environ["HOME"] = home
    started = time.time()
    try:
        runner = Run(StubApp(sandbox_root, tmp_root), "chat1", "bash", script,
                     sandbox=False, timeout=timeout, script_as_file=True)

        async def collect():
            out = ""
            async for chunk in runner.run():
                out += chunk
            return out

        out = asyncio.run(collect())
    finally:
        if saved_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = saved_home
    leftovers = [n for n in os.listdir(tmp_root) if n.startswith(".spit_cmd_")]
    return out, leftovers, time.time() - started
