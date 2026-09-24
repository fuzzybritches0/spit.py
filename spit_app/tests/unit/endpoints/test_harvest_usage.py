#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""t10 - Work.harvest_usage(): what a reply's usage object does to the counts on
the CHAT. Driven with a SimpleNamespace standing in for the Work - the method
reads `self.endpoint.usage` and `self.chat.token_usage` and nothing else, so the
real Work (which builds a server, a cache manager and the whole tool tree in
`__init__`) is not needed and nothing here reaches a socket or a data dir.

Numbers are append-only across the whole suite (TRAPS #15): this file owns t10.

  context   = the LATEST call's prompt+completion and NEVER a sum - two calls,
              the second SMALLER, the figure must go DOWN (a tool loop refreshes
              the window, it does not add the history up again);
  generated accumulates across calls;
  cached    = the latest prompt_tokens_details, or 0 FOR THAT READ - it does not
              keep the previous call's figure;
  silence   (usage falsy) changes nothing and zeroes nothing;
  a usage with prompt_tokens absent counts 0 + completion;
  and `messages` is untouched by the harvest - they are POSTed verbatim, so a
  count written into them would go to the model. Compared before/after.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from endpoint_harness import check, dumps, guarded, summary  # noqa: E402
import endpoint_harness as harness  # noqa: E402

from counts_harness import namespace  # noqa: E402  (the Work stand-in)

from spit_app.chat.work import Work  # noqa: E402
from spit_app.chat.chat import Chat  # noqa: E402  (only for the dict shape note)


class FakeChat:
    """The two fields the harvest touches."""

    def __init__(self) -> None:
        self.token_usage = {"context": 0, "generated": 0, "cached": 0}
        self.messages = [{"role": "user", "content": [{"type": "text",
                                                       "text": "mm-user-one"}]}]


def t10_harvest():
    chat = FakeChat()

    # a first reply: window fill, generated, cached.
    Work.harvest_usage(namespace(chat, {"prompt_tokens": 4100, "completion_tokens": 211,
                                        "prompt_tokens_details": {"cached_tokens": 3050}}))
    check("t10-context-is-prompt-plus-completion", chat.token_usage["context"], 4311)
    check("t10-generated-accumulates", chat.token_usage["generated"], 211)
    check("t10-cached-from-the-details-object", chat.token_usage["cached"], 3050)

    # the second call is SMALLER: `context` goes DOWN, it never sums.
    Work.harvest_usage(namespace(chat, {"prompt_tokens": 1200, "completion_tokens": 50}))
    check("t10-context-is-the-LATEST-call-and-never-a-sum",
          chat.token_usage["context"], 1250)
    check("t10-context-went-DOWN-proving-no-sum", chat.token_usage["context"] < 4311, True)
    check("t10-generated-still-accumulates", chat.token_usage["generated"], 261)
    # no details on THIS read -> cached is 0 for this read, not last call's 3050.
    check("t10-cached-is-this-reads-figure-not-the-previous-ones",
          chat.token_usage["cached"], 0)

    # silence: the endpoint said nothing -> nothing changes AND nothing zeroes.
    before = dumps(chat.token_usage)
    for silence in (None, {}, {}):
        Work.harvest_usage(namespace(chat, silence))
    check("t10-silence-changes-nothing-and-zeroes-nothing",
          dumps(chat.token_usage), before)

    # prompt_tokens absent counts 0 + completion.
    fresh = FakeChat()
    Work.harvest_usage(namespace(fresh, {"completion_tokens": 40}))
    check("t10-prompt-tokens-absent-counts-zero-plus-completion",
          (fresh.token_usage["context"], fresh.token_usage["generated"]), (40, 40))
    check("t10-prompt-tokens-absent-cached-is-zero", fresh.token_usage["cached"], 0)

    # completion_tokens absent the same way: the arithmetic never sees None.
    fresh = FakeChat()
    Work.harvest_usage(namespace(fresh, {"prompt_tokens": 77}))
    check("t10-completion-tokens-absent-is-not-a-TypeError",
          (fresh.token_usage["context"], fresh.token_usage["generated"]), (77, 0))

    # A key present but NULL is the same case - llama.cpp answers
    # `"cached_tokens": null` more often than it omits the details object, and
    # `or 0` is what keeps a None out of the arithmetic (a `+` on None is a
    # TypeError inside the end-of-reply path).
    fresh = FakeChat()
    Work.harvest_usage(namespace(fresh, {"prompt_tokens": None,
                                         "completion_tokens": None,
                                         "prompt_tokens_details": None}))
    check("t10-null-counts-are-zero-not-a-TypeError",
          (fresh.token_usage["context"], fresh.token_usage["generated"]), (0, 0))
    fresh = FakeChat()
    Work.harvest_usage(namespace(fresh, {"prompt_tokens": 10, "completion_tokens": 5,
                                         "prompt_tokens_details": {"cached_tokens": None}}))
    check("t10-null-cached_tokens-is-zero-for-that-read", fresh.token_usage["cached"], 0)
    # and a REAL zero is a zero, not a fallthrough: cached says 0, the row shows 0.
    fresh = FakeChat()
    Work.harvest_usage(namespace(fresh, {"prompt_tokens": 10, "completion_tokens": 5,
                                         "prompt_tokens_details": {"cached_tokens": 0}}))
    check("t10-cached_tokens-zero-stays-zero", fresh.token_usage["cached"], 0)

    # THE ONE THAT MATTERS MOST: `messages` are POSTed verbatim, so the harvest
    # must not write a single character of the counts into them.
    chat = FakeChat()
    messages_before = dumps(chat.messages)
    for usage in ({"prompt_tokens": 1, "completion_tokens": 2},
                  {"prompt_tokens": 3, "completion_tokens": 4,
                   "prompt_tokens_details": {"cached_tokens": 5}},
                  None):
        Work.harvest_usage(namespace(chat, usage))
    check("t10-messages-untouched-by-the-harvest", dumps(chat.messages), messages_before)
    check("t10-messages-still-carry-only-their-own-tokens",
          sorted(chat.messages[0].keys()), ["content", "role"])
    # and the counts really did move while messages stood still.
    check("t10-and-the-counts-did-move", chat.token_usage["generated"], 6)

    # The dict a CHAT starts a session with (step 2): three zeros, not Nones -
    # `+=` needs a number to add to, and the row renders a 0 where it has no
    # figure only because the count is really 0. Read out of the REAL class with
    # ast: this file's `FakeChat` carries the same literal, and a check against
    # the fake would pin the fake, which is not the code (the fake's copy is
    # pinned against this one below, so the two cannot drift).
    check("t10-the-real-Chat-initialises-the-three-counts-to-zero-not-None",
          _chat_starting_counts(), {"context": 0, "generated": 0, "cached": 0})
    check("t10-the-fake-starts-where-the-real-chat-starts",
          FakeChat().token_usage, _chat_starting_counts())


def _chat_starting_counts() -> dict:
    """The literal `Chat.__init__` assigns to `self.token_usage`, read from the
    real source (ast, so re-formatting cannot redden it and a changed VALUE
    must)."""
    import ast
    import inspect
    import textwrap
    tree = ast.parse(textwrap.dedent(inspect.getsource(Chat.__init__)))
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Attribute) and t.attr == "token_usage"
                        for t in node.targets)):
            return ast.literal_eval(node.value)
    return None


def main():
    print("INPUT MAPPING (TRAPS #13): no socket, no app - the harvest is driven with "
          "a SimpleNamespace(endpoint=..., chat=...) because it reads "
          "self.endpoint.usage and self.chat.token_usage and nothing else.")
    guarded("t10", t10_harvest)
    summary()
    return 1 if harness.fail_ else 0


if __name__ == "__main__":
    sys.exit(main())
