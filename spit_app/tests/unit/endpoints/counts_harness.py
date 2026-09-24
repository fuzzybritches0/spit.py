# SPDX-License-Identifier: GPL-2.0
"""The stub app t11 needs (imported by test_counts_row.py; NOT named test_* so
the runner's glob does not turn it into a suite file - the stub_app.py /
window_harness.py precedent, and its cross-suite import of unit:chat_smoke's
stub is that file's own precedent).

WHY A STUB OF A STUB. unit:chat_smoke's SmokeApp answers `endpoint_list()` with
`{}` - that is the GUARD path of `refresh_usage()` (`if not key[0] in
self.app.endpoint_list(): return`), so a suite built on it CANNOT see a single
probe: the counts row would only ever show the dash. `StubEndpointApp` overrides
the three endpoint methods with a real saved-shape endpoint dict, which is what
makes the probe behaviour (one per (endpoint, model) pair, cached None, stored
under the pair the probe was STARTED for) assertable at all.

Needs httpx AND textual (TRAPS #19) - run_tests.sh gates both.
"""
import asyncio
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, *[".."] * 4)))          # repo root
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "chat_smoke")))   # the stub app

from smoke_scenario import SmokeApp, fixture_chat  # noqa: E402,F401  (the SAME stub)


class StubEndpointApp(SmokeApp):
    """The WP-B stub app, but its endpoint list is real (saved shape)."""

    def __init__(self, content: dict, endpoints: dict) -> None:
        super().__init__(content)
        self.endpoints = endpoints

    def endpoint_list(self) -> dict:
        return self.endpoints

    def endpoint_list_tuple(self) -> tuple:
        return tuple((e["name"]["value"], key) for key, e in self.endpoints.items())

    def get_endpoint(self, endpoint_id: str) -> dict:
        return self.endpoints[endpoint_id]


def app_endpoint(url: str, name: str = "mm-one-endpoint", context_size: int = 0) -> dict:
    """A SAVED endpoint for the stub's list (the fields ChatSettings and
    get_context_size actually index; `timeout` NON-ZERO, see endpoint_harness)."""
    return {"name": {"value": name},
            "endpoint_url": {"value": url},
            "key": {"value": ""},
            "timeout": {"value": 5},
            "context_size": {"value": context_size},
            "reasoning_key": {"value": "reasoning_content"}}


class FakeEndpoint:
    """An endpoint whose stream() ends the way llamacpp.py's does: maybe_callback(0)
    is the LAST act of stream(). The signal is therefore POSTED before Work
    harvests and DELIVERED after it (`post_message` only queues; the handler runs
    when the coroutine next yields to the loop, and `Work.work_stream()` harvests
    the moment the await returns) - which is why the row shows THIS reply's
    numbers. `defer` is the stale-by-one control: one extra await inside stream()
    and the handler runs BEFORE the harvest."""

    def __init__(self, chat) -> None:
        self.callback = chat.chat_view.callback
        self.messages = chat.messages
        self.usage = None
        self.script = []
        self.defer = False

    async def stream(self) -> None:
        self.usage = None
        item = self.script.pop(0) if self.script else None
        if item is not None:
            self.usage = item
        self.messages.append({"role": "assistant", "reasoning": "",
                              "content": [{"type": "text", "text": "mm-reply"}]})
        self.message_index = len(self.messages) - 1
        await asyncio.sleep(0)
        if self.defer:                      # the control: signal BEFORE harvest
            self.callback(self.message_index, 0)
            await asyncio.sleep(0)
        else:
            self.callback(self.message_index, 0)


class Reply:
    """The two statements of Work.work_stream() around one stream(), with the
    REAL harvest: what a reply does to chat.token_usage and then to the row."""

    def __init__(self, chat, endpoint) -> None:
        self.chat = chat
        self.endpoint = endpoint
        self.messages = chat.messages

    async def one(self) -> None:
        from spit_app.chat.work import Work
        await self.endpoint.stream()
        Work.harvest_usage(self)


def row_text(chat) -> str:
    return str(chat.chat_settings.usage_label.content)


def namespace(chat, usage) -> object:
    """A `Work` stand-in for Work.harvest_usage - it reads self.endpoint.usage
    and self.chat.token_usage and nothing else."""
    from types import SimpleNamespace
    return SimpleNamespace(endpoint=SimpleNamespace(usage=usage), chat=chat)


async def settle(pilot, passes: int = 6) -> None:
    for _ in range(passes):
        await pilot.pause()
