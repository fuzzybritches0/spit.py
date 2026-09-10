#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Unit tests for the event loop around a `terminal` call: who blocks, and for how long.

doc/TASKS-IN-PROGRESS.md P0b-followup 2 says this tool's `time.sleep(delay)` is "a
1-second freeze of the Textual UI on every `terminal` call" and prescribes
`call_async_generator` + `await asyncio.sleep(delay)` as the fix. Measured over the
path the app actually awaits -- `chat/work.py:118` -> `tool_call.ToolCall.call()` --
the freeze is not there, and the reason is not in the tool: the dispatcher sends a
plain function call to a worker thread (`await asyncio.to_thread(...)`, `d455761`,
2026-07-28), so the sleep sleeps in the pool. Measured here: a `delay=1` call costs
1.05 s of wall clock and **53 loop ticks**, worst gap 22 ms.

Section 2 is the control, and without it section 1 proves nothing: the same
dispatcher, with `to_thread` replaced by a direct call, is **1 tick and a 1.07 s
gap** -- the reported freeze, exactly, produced on the loop by removing the one hop
that prevents it. That is DECISIONS 67's rule applied forwards: a check that passes
against the code it was written to catch means the setup is wrong, so the probe is
shown catching the stall before it is trusted to report its absence.

What IS blocking is the other part of the call, which the entry's fix shape would
move ONTO the loop: libtmux shells out to the `tmux` binary on every round-trip, and
section 3 measures a plain `term_screen()` at ~46 ms here, stalling the loop by
about its own duration. `call_async_generator` would therefore put ~46 ms of tmux
subprocess I/O on the UI thread per call to rescue a sleep that is already off it.

Nothing here changes behaviour. These checks pin a property the tool does not own --
it belongs to the dispatcher in `tool_call.py`, which no suite drives -- and the
existing suite calls `call()` directly, so it cannot see that hop regress.
"""
import asyncio
import inspect
import json
import statistics
import tempfile
import time
from pathlib import Path

from stub_app import (check, kill_private_server, stub_app, summary,
                      tmux_available, use_private_server, wait_for_text)

SOCKET = "spit-unit-terminal-loop"
HEARTBEAT = 0.02

if not tmux_available():
    print("SKIP: no tmux binary on this machine; the terminal suite cannot run")
    print("PASS: 0  FAIL: 0")
    raise SystemExit(0)

use_private_server(SOCKET)

import spit_app.tools.terminal as tool
import spit_app.tool_call as tool_call_module
from spit_app.tool_call import ToolCall


class without_the_worker_thread:
    """`asyncio` with the thread hop undone: `to_thread` runs on the caller.

    Assigning this to `spit_app.tool_call.asyncio` makes the dispatcher execute a
    tool's sync `call()` on the event loop -- what it did before `d455761`, and
    what the entry's fix shape restores for everything but the sleep. The control
    is then the same dispatcher and the same tool call, not a copy of it.
    """

    def __getattr__(self, name):
        return getattr(asyncio, name)

    async def to_thread(self, function, *args, **kwargs):
        return function(*args, **kwargs)


def dispatcher(app, root: str) -> ToolCall:
    """The shipped ToolCall, loading the real tools directory, over the stub chat."""
    custom_tools = Path(root) / "custom-tools"
    custom_tools.mkdir(exist_ok=True)
    app.settings.path["custom_tools"] = custom_tools
    call = ToolCall(app)
    app.tool_call = call
    return call


async def through_the_dispatcher(call, arguments: dict) -> str:
    """One tool call as work.py does it: await ToolCall.call(messages, ...)."""
    messages = []
    await call.call(messages, {"id": "c1", "function": {"name": "terminal",
                 "arguments": json.dumps(arguments)}}, "chat1", None)
    return messages[-1]["content"][0]["text"]


async def measure(what):
    """Run `what()` and report the event loop's own heartbeat during it.

    Wall clock cannot tell a stalled loop from a fast one; ticks and the worst gap
    between them can. The counters are zeroed after the heartbeat has settled so
    the measurement starts from a steady beat.
    """
    state = {"run": True, "ticks": 0, "worst_gap": 0.0}

    async def heartbeat():
        last = time.monotonic()
        while state["run"]:
            await asyncio.sleep(HEARTBEAT)
            now = time.monotonic()
            state["ticks"] += 1
            state["worst_gap"] = max(state["worst_gap"], now - last)
            last = now

    beat = asyncio.ensure_future(heartbeat())
    await asyncio.sleep(5 * HEARTBEAT)
    state["ticks"], state["worst_gap"] = 0, 0.0
    started = time.monotonic()
    result = what()
    if asyncio.iscoroutine(result):
        result = await result
    elapsed = time.monotonic() - started
    state["run"] = False
    await beat
    return elapsed, state["ticks"], state["worst_gap"], result


async def sections():
    print("=== 1. the shipped dispatcher keeps the loop free while the tool sleeps ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        call = dispatcher(app, root)
        tool.call(app, {"name": "t1", "input": ["echo mm-loop-token", "Enter"]}, "chat1")
        check("t1-token-reached-the-pane", wait_for_text(app, "t1", "mm-loop-token"), True)

        elapsed, ticks, worst_gap, screen = await measure(
            lambda: through_the_dispatcher(call, {"name": "t1", "delay": 1}))
        check("t1-the-delay-was-actually-slept", 1.0 <= elapsed < 2.0, True)
        check("t1-the-answer-is-the-screen", "mm-loop-token" in screen, True)
        check("t1-the-loop-kept-ticking-through-the-delay", ticks >= 10, True)
        check("t1-the-loop-never-stalled-for-the-delay", worst_gap < 0.25, True)

        elapsed, ticks, worst_gap, screen = await measure(
            lambda: through_the_dispatcher(call, {"name": "t1", "delay": 0}))
        check("t1-no-delay-is-quick", elapsed < 0.5, True)
        check("t1-no-delay-keeps-the-loop-free", worst_gap < 0.25, True)

    print("=== 2. the control: the same dispatcher without the thread hop freezes ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        call = dispatcher(app, root)
        tool.call(app, {"name": "t2", "input": ["echo mm-loop-control", "Enter"]}, "chat1")
        check("t2-token-reached-the-pane", wait_for_text(app, "t2", "mm-loop-control"), True)

        saved_asyncio = tool_call_module.asyncio
        tool_call_module.asyncio = without_the_worker_thread()
        try:
            elapsed, ticks, worst_gap, screen = await measure(
                lambda: through_the_dispatcher(call, {"name": "t2", "delay": 1}))
        finally:
            tool_call_module.asyncio = saved_asyncio
        check("t2-the-answer-is-unchanged", "mm-loop-control" in screen, True)
        check("t2-the-loop-stalled-for-the-whole-delay", worst_gap > 0.5, True)
        check("t2-the-loop-got-no-ticks-at-all", ticks <= 3, True)
        check("t2-the-freeze-is-the-reported-one", 1.0 <= elapsed < 2.0, True)

    print("=== 3. the tmux round-trips block on their own: the sleep is not all of it ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        call = dispatcher(app, root)
        tool.call(app, {"name": "t3", "input": ["echo mm-capture-cost", "Enter"]}, "chat1")
        check("t3-token-reached-the-pane", wait_for_text(app, "t3", "mm-capture-cost"), True)

        def capture():
            return tool.Terminal(app, "chat1", False).term_screen("t3")

        # Medians of three, and a comparison of two gaps measured in this process on
        # this box: the assertion is about the hop, not about how fast tmux is here.
        on_loop = [await measure(capture) for _ in range(3)]
        duration = statistics.median(run[0] for run in on_loop)
        on_loop_gap = statistics.median(run[2] for run in on_loop)
        check("t3-a-capture-is-not-free", duration >= 0.005, True)
        check("t3-a-capture-on-the-loop-stalls-it-by-its-own-duration",
              on_loop_gap >= 0.5 * duration, True)

        dispatched = [await measure(lambda: through_the_dispatcher(
            call, {"name": "t3", "delay": 0})) for _ in range(3)]
        check("t3-and-still-returns-the-screen", "mm-capture-cost" in dispatched[0][3], True)

        # THE BURST (state layer, DECISIONS 70). The assertion above this file
        # shipped with compared ONE dispatched capture's gap against ONE capture
        # run on the loop, at a margin of 0.5. It was calibrated on the 46 ms
        # term_screen of the object layer: on the loop a 46 ms capture pushed the
        # heartbeat gap to ~66 ms against the dispatcher's ~22 ms, and 22 <= 33
        # held. The state layer made the SAME call cost 2 tmux invocations and
        # ~17 ms (one narrow `list-panes -a` plus the `capture-pane`), so a single
        # on-loop gap is now ~36 ms -- only about the 20 ms heartbeat plus the
        # capture -- and the ratio had nothing left to measure: the tool got
        # faster, which is the point of the change. Making the capture slower
        # again to feed the ratio would be absurd, and deleting the check would
        # throw away the only probe of the hop's SECOND job: the first two
        # sections cover a sleep held off the loop, this one covers the tmux
        # subprocess I/O itself. So compare what the hop is actually protecting
        # the loop from -- a BURST of captures back to back (5 on the loop = ~99 ms
        # of worst gap here; the same 5 through the dispatcher = 22 ms and the
        # loop keeps ticking), same 0.5 margin, measured 22 <= 49. The check
        # stays red if the hop is removed: see section 2 for the same surgery.
        def burst_on_loop():
            for _ in range(5):
                capture()

        async def burst_through_the_hop():
            screen = None
            for _ in range(5):
                screen = await through_the_dispatcher(call, {"name": "t3", "delay": 0})
            return screen

        burst = [await measure(burst_on_loop) for _ in range(3)]
        burst_gap = statistics.median(run[2] for run in burst)
        check("t3-a-burst-of-captures-on-the-loop-is-felt", burst_gap >= duration, True)
        burst_dispatched = [await measure(burst_through_the_hop) for _ in range(3)]
        dispatched_burst_gap = statistics.median(run[2] for run in burst_dispatched)
        check("t3-the-hop-keeps-the-tmux-work-off-the-loop-too",
              dispatched_burst_gap <= 0.5 * burst_gap, True)
        check("t3-the-burst-still-returns-the-screen",
              "mm-capture-cost" in burst_dispatched[0][3], True)

    print("=== 4. which branch of the dispatcher the shipped tools land on ===")
    with tempfile.TemporaryDirectory() as root:
        app = stub_app(root)
        call = dispatcher(app, root)
        check("t4-terminal-is-a-plain-function",
              inspect.isfunction(tool.call) and not inspect.iscoroutinefunction(tool.call),
              True)
        check("t4-the-loaded-table-handles-terminal-with-call",
              "call" in call.tools["terminal"] and
              "call_async_generator" not in call.tools["terminal"], True)
        check("t4-so-does-lsterm", "call" in call.tools["lsterm"], True)
        # load_tools() loads each file under its own name, so the table holds a
        # different module object than the one this test imported: the two are
        # tied by the file the function was compiled from.
        loaded = call.tools["terminal"]["call"]
        check("t4-section-1-ran-through-the-thread-branch",
              inspect.isfunction(loaded) and not inspect.iscoroutinefunction(loaded) and
              loaded.__code__.co_filename == tool.__file__, True)


try:
    asyncio.run(sections())
finally:
    kill_private_server(SOCKET)

summary()
