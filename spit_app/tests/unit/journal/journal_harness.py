#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""The journal suite's harness: the two things `journal.py` asks an app for.

Deliberately NOT named `test_*` (the `stub_app.py` / `window_harness.py` /
`endpoint_harness.py` precedent): the runner globs `test_*.py` and would turn a
harness into a suite file and its helpers into checks.

What the tool asks is `app.settings.path["data"]` and
`app.settings.tool_settings`, and NOTHING else - that small surface is the
point of building it in-process, and t2 asserts it by driving `call` with only
this object present. `path["data"]` points into `./fixtures/journal-data`, the
generated, disposable home every suite in this repo uses: the real data dir is
the USER's, and a test that wrote a journal there would leave a file behind in
the place the app itself reads.
"""
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                *[".."] * 4)))

from spit_app.tool_call import load_module_from_path

FIXTURES = Path(__file__).parent / "fixtures"
DATA = FIXTURES / "journal-data"

# The tool loaded the way the app loads it - `load_module_from_path`, the one
# function `tool_call.load_tools` uses for every tool in the tree - so the
# suite drives the module the app would drive, from the path the app reads, and
# nothing about it is a test-only copy. That import is also what TRAPS #19 is
# about: `tool_call` pulls `spit_app.arguments` and the stdlib and NOTHING
# else, which is why this row runs on the bare interpreter (t1).
TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
journal = load_module_from_path("tools.journal", TOOLS_DIR / "journal.py")


class StubSettings:
    def __init__(self, data_dir: Path) -> None:
        self.path = {"data": data_dir}
        self.tool_settings = {}


class StubApp:
    def __init__(self, data_dir: Path = DATA) -> None:
        self.settings = StubSettings(data_dir)


def prepare() -> Path:
    """A clean data dir for one group. The journal dir itself is NOT created:
    the tool makes it on its first write, and a setup that pre-made it would
    hide a refusal to create it behind this file."""
    if DATA.exists():
        shutil.rmtree(DATA)
    DATA.mkdir(parents=True)
    return DATA


def teardown() -> None:
    if os.environ.get("KEEP_FIXTURES") != "1" and FIXTURES.exists():
        shutil.rmtree(FIXTURES)


def journal_file(chat_id: str, data_dir: Path = DATA) -> Path:
    return data_dir / "journal" / f"{chat_id}.txt"


def set_cap(app, value) -> None:
    """A user's saved setting, in the shape `tool_settings` really holds - the
    one `load_user_settings` copies out of. `None` is the blanked field
    `store_values` leaves behind, not an invented case."""
    app.settings.tool_settings["journal"] = {
        "journal_max_chars": {"value": value}}


def entry_text(word: str, filler: int = 0) -> str:
    body = f"Branch: b-{word}\nLeft: l-{word}"
    if filler:
        body += "\n" + ("x" * filler)
    return body
