# SPDX-License-Identifier: GPL-2.0
"""Stand-ins for the modules `chat/work.py` imports, so it can be loaded by the
bare system python3 (TRAPS #19: the app's dependencies are not installed there).

work.py needs Textual (through `chat.textual_message`) and httpx (through
`endpoints.manage_cache` and `endpoints.llamacpp`) only to build its endpoint in
`__init__`. The prompt assembly tested here touches none of that, so these stubs
exist to satisfy the import, and nothing else: no stub is ever called. The
pattern is the one `tests/unit/render/stub_textual.py` established.
"""
import sys
import types

STUBBED = {
    "httpx": (),
    "spit_app.endpoints.llamacpp": ("LlamaCppEndpoint",),
    "spit_app.endpoints.manage_cache": ("ManageCache",),
    "spit_app.chat.textual_message": ("RemoveMessage",),
}


class Stub:
    """Placeholder whose only job is to exist under an expected attribute name."""


def install() -> None:
    for name, attributes in STUBBED.items():
        module = types.ModuleType(name)
        for attribute in attributes:
            setattr(module, attribute, Stub)
        sys.modules[name] = module
