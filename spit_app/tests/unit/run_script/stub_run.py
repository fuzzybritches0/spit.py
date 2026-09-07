# SPDX-License-Identifier: GPL-2.0
"""A stand-in for `Run` and the helpers that drive `run_script` through it.

`run_script` is a tool *module*: importing it is fine with the bare test python
(it needs `Run` and `tool_call`, both of which import nothing but the stdlib),
but calling it builds a real `Run`, which wants the Textual app, a chat widget
and bwrap. What these tests are about is the *call the tool makes* -- which
payload for which interpreter, and which switches -- so `Run` is replaced by a
spy that records its constructor arguments and yields one distinctive line.

What the recorded payload actually does when an interpreter runs it is the other
file's business (`test_delivery.py`, which runs the real bash/python3/perl with
no stub at all). Nothing here fakes an outcome: a call that built no `Run` is
reported as such and the caller asserts it, so a refusal cannot pass as a run.

`load_user_settings` writes user overrides into the module-level `SETTINGS`
dict, so they would leak from one check into the next; `call` snapshots and puts
it back, which keeps the order of the tests irrelevant.
"""
import asyncio
import types

import spit_app.tools.run_script as run_script


class SpyRun:
    """Records what it was constructed with; yields a line no tool could print."""

    built = []

    def __init__(self, app, chat_id, cmd, script, sandbox, timeout, **kwargs):
        self.chat_id = chat_id
        self.cmd = cmd
        self.script = script
        self.sandbox = sandbox
        self.timeout = timeout
        self.kwargs = kwargs
        SpyRun.built.append(self)

    async def run(self):
        yield "SPY-RAN-THIS\n"


def stub_app(tool_settings=None):
    """The only thing the tool asks of the app is `settings.tool_settings`."""
    return types.SimpleNamespace(
        settings=types.SimpleNamespace(tool_settings=tool_settings or {}))


def call(user_app=None, **arguments):
    """One call of the tool with the spy installed: (yielded text, [SpyRun])."""
    SpyRun.built = []
    saved_module_run, run_script.Run = run_script.Run, SpyRun
    saved_settings = {key: dict(value)
                      for key, value in run_script.SETTINGS.items()}
    target = user_app if user_app is not None else stub_app()

    async def drain():
        out = ""
        async for chunk in run_script.call_async_generator(target, arguments,
                                                           "chat1"):
            out += chunk
        return out

    try:
        output = asyncio.run(drain())
    finally:
        run_script.Run = saved_module_run
        run_script.SETTINGS.clear()
        run_script.SETTINGS.update(saved_settings)
    return output, SpyRun.built


def app_with(interpreters):
    """An app whose `interpreters` user setting says `interpreters`."""
    return stub_app({run_script.NAME: {"interpreters": {"value": interpreters}}})


def build(interpreter, script, allowed=None, **arguments):
    """The call a tool invocation makes: (SpyRun or None, yielded text).

    None means nothing was run -- the tool refused -- and every caller says so
    explicitly rather than reading attributes off a missing run.
    `allowed`, when given, is the `interpreters` setting the call runs under;
    without it the module default applies.
    """
    user_app = app_with(allowed) if allowed is not None else None
    text, builds = call(user_app, interpreter=interpreter, script=script,
                        **arguments)
    return (builds[0] if len(builds) == 1 else None), text
