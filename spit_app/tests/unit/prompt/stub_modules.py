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
    # `EndpointFailure` since P19/WP-2: work.py imports the typed failure beside
    # the endpoint class to decide retry-or-report. The stub only has to EXIST
    # under that name (class `Stub` is not instantiated here), and the import
    # line is what the bare interpreter fails on without it.
    # `DeterministicFailure` since P19/WP-4, the same reason and the same shape:
    # `report_failure` asks `isinstance(exception, DeterministicFailure)` to keep
    # the modal for a refusal the app cannot answer for.
    "spit_app.endpoints.llamacpp": ("LlamaCppEndpoint", "EndpointFailure", "DeterministicFailure"),
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
