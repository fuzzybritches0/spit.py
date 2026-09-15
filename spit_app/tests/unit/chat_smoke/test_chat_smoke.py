#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""The WP-B proof pair: the differential, and the accessor contract it protects.

t1  THE DIFFERENTIAL (doc/UI-ONDEMAND-LOADING.md WP-B Accept, TRAPS #14/#18):
    scripted_smoke.run_scenario() walks a real Chat - mount, focus, edit_on/off,
    the message-level add/remove actions, the three stream signals, undo/redo,
    abort - over a generated fixture, and every step is dumped as plain data
    (message roles, per-widget cnt keys, rendered Part text, cots visibility,
    focus, the undo list, the chat JSON written so far, scroll position). That
    dump must stay byte-identical to `golden.txt`, which was generated from
    f201700 - the tip BEFORE the index-accessor refactor - with:

        git archive f201700 | tar -x -C /tmp/spit-base
        python3 spit_app/tests/unit/chat_smoke/smoke_scenario.py \
            --tree /tmp/spit-base --out golden.txt

    A green suite cannot see an accessor refactor that quietly addressed a
    different widget; this can, and it re-pins the whole coupling surface for
    WP-C/D/E: any behaviour drift in the windowed refactor shows up here as the
    differing step, on purpose. (When a WP *intends* a behaviour change, the
    golden is re-pinned deliberately and the commit says which steps moved.)

t2  THE ACCESSOR CONTRACT - `window_start = 0` and the invariant
    len(children) == len(messages) - window_start at every step, and
    widget()/widget_index()/last_child()/child_position() agreeing with the raw
    child list they replaced (that agreement IS "provably identical").
"""
import asyncio
import difflib
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                *[".."] * 4)))

import smoke_scenario  # noqa: E402  (the harness, same directory)

GOLDEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden.txt")

pass_ = 0
fail_ = 0


def check(name, got, expected):
    global pass_, fail_
    if got == expected:
        pass_ += 1
    else:
        fail_ += 1
        print(f"FAIL: {name}\n  got:      {got!r}\n  expected: {expected!r}")


def collect():
    """Run the scripted walk once, keeping per-step facts AND the accessor
    state of the live view (the scenario itself stays version-agnostic so it can
    drive the pre-refactor tree; the accessor checks live here)."""
    steps = []

    def on_step(name, app, chat):
        view = chat.chat_view
        children = list(view.children)
        steps.append({
            "name": name,
            "facts": smoke_scenario.facts(app, chat),
            "window_start": view.window_start,
            "window_consistent": view.window_consistent(),
            "forward_ok": all(view.widget(index) is child
                              for index, child in enumerate(children)),
            "reverse_ok": all(view.widget_index(child) == index
                              for index, child in enumerate(children)),
            "last_ok": (view.last_child() is children[-1] if children
                        else view.last_child() is None),
        })

    asyncio.run(smoke_scenario.run_scenario(on_step))
    return steps


def blocks(text):
    """The dump as {step-name: [lines]}."""
    out, name = {}, None
    for line in text.splitlines():
        if line.startswith("=== STEP "):
            name = line[len("=== STEP "):]
            out[name] = []
        elif name is not None:
            out[name].append(line)
    return out


def test_differential(steps):
    with open(GOLDEN) as file:
        golden = file.read()
    produced = smoke_scenario.dump([(step["name"], step["facts"]) for step in steps])
    gold, mine = blocks(golden), blocks(produced)
    check("t1-steps-in-golden", sorted(mine.keys()), sorted(gold.keys()))
    for name in sorted(gold.keys()):
        if mine.get(name) != gold[name]:
            delta = "\n".join(list(difflib.unified_diff(
                gold[name], mine.get(name, []), "golden(f201700)", "tree", lineterm=""))[:24])
            check(f"t1-step-identical[{name}]", "\n" + delta, "\n(no diff)")
        else:
            check(f"t1-step-identical[{name}]", 0, 0)


def test_accessors(steps):
    for step in steps:
        check(f"t2-window-start-zero[{step['name']}]", step["window_start"], 0)
        check(f"t2-invariant[{step['name']}]", step["window_consistent"], True)
        check(f"t2-forward-map[{step['name']}]", step["forward_ok"], True)
        check(f"t2-reverse-map[{step['name']}]", step["reverse_ok"], True)
        check(f"t2-last-child[{step['name']}]", step["last_ok"], True)

    # The out-of-window answers, on a view with children mounted: the tolerant
    # accessor says None, the strict one raises IndexError (the exception
    # `children[i]` raised), and a foreign widget has no index at all.
    app = smoke_scenario.SmokeApp(smoke_scenario.fixture_chat())

    async def contract():
        async with app.run_test(size=smoke_scenario.APP_SIZE) as pilot:
            await smoke_scenario.settle(pilot)
            view = app.chat.chat_view
            await view.load()
            await smoke_scenario.settle(pilot)
            check("t2-empty-is-consistent", view.window_consistent(), True)
            check("t2-below-window", view.widget(-1), None)
            check("t2-above-window", view.widget(len(view.messages)), None)
            check("t2-widget_index-foreign", view.widget_index(app.chat.text_area), None)
            check("t2-child_position-first", view.child_position(0), 0)
            check("t2-child_position-append-spot",
                  view.child_position(len(view.children)), len(view.children))
            check("t2-child_position-past-end",
                  view.child_position(len(view.children) + 1), None)
            for name, index in (("below", -1), ("above", len(view.messages))):
                try:
                    view.require_widget(index)
                    check(f"t2-require-raises-{name}", "no raise", "IndexError")
                except IndexError:
                    check(f"t2-require-raises-{name}", "IndexError", "IndexError")
            check("t2-data-list-identity", view.messages is app.chat.messages, True)
            check("t2-window-consistent-after-load", view.window_consistent(), True)

    asyncio.run(contract())


def summary():
    print()
    print(f"PASS: {pass_}  FAIL: {fail_}")


if __name__ == "__main__":
    walked = collect()
    test_differential(walked)
    test_accessors(walked)
    summary()
    sys.exit(1 if fail_ else 0)
