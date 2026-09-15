# SPDX-License-Identifier: GPL-2.0
"""Shared harness for unit:chat_window (imported by the test_*.py files; the
runner's glob deliberately does not match this name - the stub_app.py /
anchored_app.py precedent).

Needs the app's Textual (TRAPS #19): run it with ~/.venv-spit, built by
spit_app/tests/create_venv.sh. run_tests.sh enforces the dependency and
reports FAIL-with-remedy when it is missing - never a silent zero.

The stub app and the FakeWork are IMPORTED from unit:chat_smoke's
smoke_scenario.py - deliberately the SAME stub that makes the WP-B differential
machine-independent (in-memory read_json/write_json so a fixture chat can
never reach the user's real data dir, endpoint stubs, a fake `#side-panel`).
Cross-suite import is new here and is recorded as such; the alternative -
copying the stub - would let the two copies drift.

The 1000-message fixture is GENERATED, never committed (TRAPS #10), with the
distinctive `mm-open-NNNN` token style (TRAPS #8).

FrameSpy: the WP-A frame instrument (a copy of the ~25 lines of
tests/unit/anchored/anchored_app.py, attributed there) - one call to
App._display is one EMITTED frame; `bad_frames(row)` are the frames showing
the tracked widget anywhere but `row`, i.e. painted jumps. Copied rather than
imported so the two suites stay independently liftable.
"""
import hashlib
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, *[".."] * 4)))          # repo root
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "chat_smoke")))  # the stub app

from smoke_scenario import (APP_SIZE, FakeWork, SmokeApp, fixture_settings,  # noqa: E402
                            settle)

BIG_N = 1000


class WindowApp(SmokeApp):
    """The SAME stub app as the WP-B differential, but with the real
    `spit_app/styles.css`: the window's whole contract is viewport geometry,
    and without the app's stylesheet the messages lay out at zero height and
    every viewport computation goes vacuous (which is exactly what the
    `scroll_y=0`-everywhere golden of chat_smoke shows - fine for a data
    differential, useless for scroll checks). Absolute CSS_PATH so it resolves
    from this file's module, not from a package-relative path."""

    CSS_PATH = os.path.join(os.path.abspath(os.path.join(_HERE, *[".."] * 4)),
                            "spit_app", "styles.css")

def big_fixture(n: int = BIG_N) -> dict:
    """The 1k-message fixture: alternating user/assistant turns, one short
    line each, distinctive token per message."""
    messages = []
    for i in range(n):
        role = "user" if i % 2 == 0 else "assistant"
        messages.append({"role": role,
                         "content": [{"type": "text", "text": f"mm-open-{i:04d} line"}]})
    return {"ctime": "2026-01-01T00:00:00", "settings": fixture_settings(),
            "messages": messages}


def store_md5(app) -> str:
    return hashlib.md5(json.dumps(app.store, sort_keys=True).encode()).hexdigest()


def first_visible(view):
    return next((c for c in view.children if c.region.bottom > view.region.y), None)


class FrameSpy:
    """Record the tracked widget's SCREEN row of every frame the app emits
    (the anchored_app.py instrument; see its docstring for the mechanism)."""

    def __init__(self, app, tracked=None) -> None:
        self.app = app
        self.tracked = tracked
        self.frames: list[int] = []
        self._orig = None

    def install(self) -> "FrameSpy":
        self._orig = self.app._display

        def spy(screen, renderable, *args, **kwargs):
            self.frames.append(self.tracked.region.y if self.tracked is not None else -1)
            return self._orig(screen, renderable, *args, **kwargs)

        self.app._display = spy
        return self

    def remove(self) -> None:
        if self._orig is not None:
            self.app._display = self._orig
            self._orig = None

    def clear(self) -> None:
        self.frames.clear()

    def bad_frames(self, expected_row: int) -> list[int]:
        return [f for f in self.frames if f != expected_row]


pass_ = 0
fail_ = 0


def check(name, got, expected):
    global pass_, fail_
    if got == expected:
        pass_ += 1
    else:
        fail_ += 1
        print(f"FAIL: {name}\n  got:      {got!r}\n  expected: {expected!r}")


def summary():
    print()
    print(f"PASS: {pass_}  FAIL: {fail_}")
