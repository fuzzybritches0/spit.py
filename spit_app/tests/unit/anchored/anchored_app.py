# SPDX-License-Identifier: GPL-2.0
"""Shared harness for unit:anchored (imported by the test_*.py files; the
runner's glob deliberately does not match this name - the unit:terminal
stub_app.py precedent).

Needs the app's Textual (TRAPS #19): run it with ~/.venv-spit, built by
spit_app/tests/create_venv.sh. run_tests.sh enforces the dependency and
reports FAIL-with-remedy when it is missing - never a silent zero.

Everything here is the headless instrument the P8 probes measured with,
rebuilt from /tmp/anchor-probe/probe.py, probe6.py, probe7.py: an
App.run_test app hosting a 10-row viewport in an 80x12 terminal with 3-row
message widgets, and the frame spy on App._display - the instrument that
turns "the correction lands in the same frame" into an assertion: one call
is one EMITTED frame, so a frame showing the tracked widget at the wrong
screen row is a painted jump, and the pinned widget's contract is that no
such frame exists.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                *[".."] * 4)))

from textual.app import App, ComposeResult
from textual.containers import VerticalScroll  # the defect control (t1)
from textual.widgets import Static

from spit_app.chat.anchored_scroll import AnchoredScroll  # noqa: F401  (the widget under test)

VIEW_H = 10      # viewport rows
MSG_H = 3        # rows per message
OLD_H = 4        # rows of a prepended "older message"
SCROLL_Y = 15    # the probes' scroll position: top edge of message 5
APP_SIZE = (80, 12)


def make_msg(label: str, height: int = MSG_H) -> Static:
    s = Static(label)
    s.styles.height = height
    return s


class ScrollApp(App[None]):
    """The container under test, optionally with Textual's bottom anchor armed
    at compose time - the state ChatView.__init__ creates with self.anchor()."""

    def __init__(self, scroll_cls: type, bottom_anchor: bool = False) -> None:
        super().__init__()
        self.scroll_cls = scroll_cls
        self.bottom_anchor = bottom_anchor

    def compose(self) -> ComposeResult:
        c = self.scroll_cls()
        c.styles.height = VIEW_H
        c.styles.scrollbar_size_vertical = 0
        if self.bottom_anchor:
            c.anchor()
        self.container = c
        yield c


async def setup(app: ScrollApp, pilot, n: int = 20, scroll_y: int = SCROLL_Y):
    """Mount n 3-row messages and scroll so message scroll_y // MSG_H sits
    with its top edge exactly at the viewport top; return (container, anchor)."""
    c = app.container
    await c.mount(*[make_msg(f"MSG-{i}") for i in range(n)])
    await pilot.pause()
    # scroll_to funnels through scroll(), which releases a built-in bottom
    # anchor exactly as a user scroll would - the setup state every probe used.
    c.scroll_to(0, scroll_y, animate=False)
    await pilot.pause()
    anchor = c.children[scroll_y // MSG_H]
    return c, anchor


async def settle(pilot, passes: int = 6) -> None:
    """Let layout passes run and frames be emitted (the probes' pause loops)."""
    for _ in range(passes):
        await pilot.pause()


class FrameSpy:
    """Record the tracked widget's SCREEN row of every frame the app emits.

    Wrap App._display: each call is one emitted frame, and it happens after
    compositing, so the tracked region is what the user would see. Call
    bad_frames(row) for the frames that show the widget anywhere but `row`.
    """

    def __init__(self, app: App, tracked=None) -> None:
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
