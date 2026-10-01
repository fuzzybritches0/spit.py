#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""The proof pair: the differential dump, and the invariant that dump protects.

t1  THE DIFFERENTIAL (TRAPS #14/#18):
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

    A green suite cannot see a change to WHICH widget a site addresses; this
    can. The golden is an old tree's output, and it survived the accessor
    refactor (WP-B), the sliding window (WP-C/D/E) and the revert of all of it
    (DECISIONS 89) because what all of those share with the base tree is exactly
    what it pins. Any drift shows up as the differing step, on purpose. (When a
    change *intends* a behaviour change, the golden is re-pinned deliberately
    and the commit says which steps moved.)

t2  THE WHOLE-HISTORY CONTRACT - the widget tree mirrors the data at every step:
    `len(children) == len(messages)`, `children[i].message is messages[i]`, the
    last child projects the last message, `is_present()` agrees with the child
    list on BOTH bounds (a negative index is not a message), and
    `mount_message()` bounds-checks the data before it mounts anything and hands
    back the widget it mounted.
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
    """Run the scripted walk once, keeping per-step facts AND the state of the
    live view (the scenario itself stays version-agnostic so it can drive an
    older tree; the invariant checks live here)."""
    steps = []

    def on_step(name, app, chat):
        view = chat.chat_view
        children = list(view.children)
        projected = (len(children) == len(chat.messages)
                     and all(child.message is chat.messages[index]
                             for index, child in enumerate(children)))
        steps.append({
            "name": name,
            "facts": smoke_scenario.facts(app, chat),
            "projected": projected,
            "tail_ok": (children[-1].message is chat.messages[-1] if children
                        else not chat.messages),
            "present_ok": (all(view.is_present(index) for index in range(len(children)))
                           and not view.is_present(len(children))),
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


def test_whole_history(steps):
    for step in steps:
        check(f"t2-tree-is-the-history[{step['name']}]", step["projected"], True)
        check(f"t2-tail-child-is-tail-message[{step['name']}]", step["tail_ok"], True)
        check(f"t2-is_present-both-bounds[{step['name']}]", step["present_ok"], True)

    # The two bounds and the mount contract, on a view with the fixture loaded.
    app = smoke_scenario.SmokeApp(smoke_scenario.fixture_chat())

    async def contract():
        async with app.run_test(size=smoke_scenario.APP_SIZE) as pilot:
            await smoke_scenario.settle(pilot)
            view = app.chat.chat_view
            await view.load()
            await smoke_scenario.settle(pilot)
            check("t2-data-list-identity", view.messages is app.chat.messages, True)
            check("t2-is_present-first", view.is_present(0), True)
            check("t2-is_present-last", view.is_present(len(view.children) - 1), True)
            check("t2-is_present-past-end", view.is_present(len(view.children)), False)
            check("t2-is_present-negative-is-not-a-message", view.is_present(-1), False)
            for name, index in (("below", -1), ("above", len(view.messages))):
                try:
                    await view.mount_message(index)
                    check(f"t2-mount_message-raises-{name}", "no raise", "IndexError")
                except IndexError:
                    check(f"t2-mount_message-raises-{name}", "IndexError", "IndexError")
                    check(f"t2-mount_message-raised-without-mounting-{name}",
                          len(view.children), len(view.messages))
            # The tail: the dict in the data first, then the mount, and the
            # widget that comes back IS the one at the end of the tree.
            tail = {"role": "user", "content": [{"type": "text", "text": "t2-tail"}]}
            app.chat.messages.append(tail)
            widget = await view.mount_message(len(app.chat.messages) - 1)
            await smoke_scenario.settle(pilot)
            check("t2-mount_message-tail-returns-the-tail",
                  widget is view.children[-1] and widget.message is tail, True)
            # Below the top: mounted at the neighbour's position, not appended.
            head = {"role": "user", "content": [{"type": "text", "text": "t2-head"}]}
            app.chat.messages.insert(0, head)
            widget = await view.mount_message(0)
            await smoke_scenario.settle(pilot)
            check("t2-mount_message-at-the-top-uses-the-neighbour",
                  widget is view.children[0] and widget.message is head, True)

    asyncio.run(contract())


def summary():
    print()
    print(f"PASS: {pass_}  FAIL: {fail_}")


if __name__ == "__main__":
    walked = collect()
    test_differential(walked)
    test_whole_history(walked)
    summary()
    sys.exit(1 if fail_ else 0)
