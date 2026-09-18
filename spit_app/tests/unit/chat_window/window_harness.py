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

WP-D adds the three things the scroll triggers need: `wheel_event` /
`wheel_scroll` (a real wheel notch, the only way to drive a trigger headless),
`CallCount` (count calls to one method of one widget, forwarding unchanged), and
`freeze_triggers` (hold the triggers off for a check that is about the window -
see its docstring for why the WP-C files need it).

WP-D also adds the two instruments the FIRST WP-D suite needed, both learned the
hard way and both of the same kind - they replace a wait on the suite's own clock
with a wait on the widget's state, the lesson `unit:terminal` wrote into
`doc/TESTING.md`: `rest()` (wait until the view has genuinely come to rest, because
`window_consistent()` is a quiescence invariant and a fixed number of pauses can
land inside a settle's mount batch), and `freeze_settle` (take the debounce away so
that "this burst never settles" is a fact about the widget rather than about how
fast the machine happens to be).
"""
import hashlib
import json
import os
import time
import sys

from textual.events import MouseScrollDown, MouseScrollUp

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


def wheel_event(view, up: bool = True, step: int = 1):
    """A mouse-wheel notch INSIDE the ChatView, built the way Textual's own mouse
    handler would build it and delivered with `app.screen._forward_event`.

    It is the only way a headless suite can scroll the view the way a hand does,
    and the WP-D triggers are deliberately driven by a scroll rather than by an API
    call, so they cannot be tested without it. `step` is the notches in one event:
    one is a notch, and a burst is a loop of these, never a `scroll_to` - that is
    the user path that RELEASES follow-bottom, so it is a different experiment
    (see the release checks in test_window_triggers.py, which use it on purpose).
    """
    region = view.region
    scroll_y = -step if up else step
    return (MouseScrollUp if up else MouseScrollDown)(
        view, region.x + 1, region.y + 1, 0, scroll_y, 0,
        False, False, False)


async def wheel_scroll(app, pilot, view, notches: int, up: bool = True) -> None:
    """`notches` wheel events, one pause between each: a continuous scroll."""
    for _ in range(notches):
        app.screen._forward_event(wheel_event(view, up))
        await pilot.pause()


def freeze_settle(view):
    """Take the settled-scroll debounce away from ONE view; everything else stays.

    The WP-D checks that need "a scroll that never stops" cannot get it by timing.
    The settle is a wall-clock timer (`SCROLL_SETTLE_DELAY`, 0.15 s) and a headless
    notch costs a frame plus the message pump: measured 66-71 ms per notch of a
    plain burst and 64 ms deep in a sliding window, so a 200-notch burst takes ~14 s
    and the timer expires inside it - measured 17 settles during one such burst, and
    3 during a 30-notch burst taken where every notch mounts. "Continuous scroll"
    is therefore not something the harness can produce by not waiting; it is
    produced by removing the timer, which is one instance attribute on the one
    method that arms it. `thaw_settle` puts the real method back.
    """
    view._arm_scroll_settle = lambda: None


def thaw_settle(view):
    if "_arm_scroll_settle" in vars(view):
        del view._arm_scroll_settle


def at_rest(view) -> bool:
    """True when the view is mutating nothing: no page operation in flight and no
    settle pending.

    Both flags are taken synchronously with their work (`load_older`/`load_newer`
    and `prune` set `_window_page_op` before their first await, `_scroll_settled`
    clears `_settle_timer` before its first), so there is no await point between
    "an operation exists" and "the flag says so" - which is what makes this a
    sound predicate rather than a lucky sample.
    """
    return not view._window_page_op and view._settle_timer is None


async def rest(pilot, view, ceiling: float = 20.0) -> bool:
    """Wait until the view has come to rest, then two more frames.

    `settle()` waits a fixed number of frames; that is the wrong wait here, because
    the settle callback is a wall-clock timer that fires whenever the pump next
    yields, and its page operation is a mount batch of its own. A check taken
    `settle()` after a burst can therefore land INSIDE that batch - and
    `window_consistent()` is documented as an invariant of QUIESCENCE (`_grow_up`
    moves `lo` after its batch, `prune` after its removals), so a sample taken
    mid-batch reads False with nothing wrong. Measured: 231 such samples in four
    walks of this shape, and ZERO once the sample waits for rest
    (/tmp/wp-d3-probe-race.py, /tmp/wp-d3-probe-guard.py). That is the same lesson
    `unit:terminal` wrote down: wait for the widget's state, not for your own clock.

    Returns whether rest was reached - a caller that asserts the invariant asserts
    this too, so a ceiling breach is a red check rather than a vacuous one.
    """
    deadline = time.monotonic() + ceiling
    stable = 0
    while time.monotonic() < deadline:
        await pilot.pause()
        stable = stable + 1 if at_rest(view) else 0
        if stable >= 2:
            await pilot.pause()
            return at_rest(view)
    return at_rest(view)


def thaw_triggers(view):
    """Undo `freeze_triggers` on the same widget: dropping the instance attribute
    returns the class's own predicate, so the check that follows runs the real
    thing. (Setup frozen, experiment live - the starved-view check needs both.)"""
    if "_triggers_frozen" in vars(view):
        del view._triggers_frozen


def freeze_triggers(view):
    """Hold the WP-D scroll triggers off for a check that is about the WINDOW.

    The triggers are live on every ChatView, so a check that scrolls the view as
    its SETUP now also pages history in and prunes at the settle - which rewrites
    the page-operation arithmetic a WP-C check is measuring (measured: t2's
    `load_older(25)` at a mid-window scroll reads (944, 981)/37 with the triggers
    live, because the settle pruned both ends back to the margin: the WP-D design
    working as specified, and not what t2 is about). t10 runs the SAME walk with
    the triggers live and asserts the pruning.

    It patches the ONE predicate every trigger path asks first, so nothing else is
    faked: the pin, the anchor, the page operations and the debounce timer are the
    real ones. An instance attribute, so it cannot leak into another check.
    """
    view._triggers_frozen = lambda: True


class CallCount:
    """Count calls to one method of ONE widget, and forward them unchanged.

    An instance attribute shadows the class method, which is exactly how Textual
    resolves a `watch_*` hook too (reactive.py:394 does the getattr on the
    instance), so this sees what the reactive machinery sees - a class-level patch
    would count every ChatView in the app and survive the test. `wrap` keeps the
    original behaviour intact: the counter never changes what the call does, and
    an async method stays awaitable because the result is returned, not consumed.
    """

    def __init__(self, target, method_name: str) -> None:
        self.target = target
        self.method_name = method_name
        self.original = getattr(target, method_name)
        self.calls: list[tuple] = []

    def install(self) -> "CallCount":
        original = self.original

        def wrapper(*args, **kwargs):
            self.calls.append(args)
            return original(*args, **kwargs)

        setattr(self.target, self.method_name, wrapper)
        return self

    def remove(self) -> None:
        setattr(self.target, self.method_name, self.original)

    @property
    def count(self) -> int:
        return len(self.calls)


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
