# SPDX-Liicense-Identifier: GPL-2.0
import os
import asyncio
from copy import deepcopy
from spit_app.endpoints.llamacpp import LlamaCppEndpoint, EndpointFailure
from .textual_message import RemoveMessage
from spit_app.endpoints.manage_cache import ManageCache

TOOL_PROMPT = "# FUNCTION CALLING INSTRUCTIONS\n\nAll of your function calls are rendered in human-readable form for the user to inspect. The user is also informed about the function call results and can see the tool response message. DO NOT REPEAT THEM!\n\n"

class Work:
    def __init__(self, chat) -> None:
        self.chat = chat
        self.chat_view = chat.chat_view
        self.cs = chat.cs
        self.app = chat.app
        self.settings = chat.app.settings
        self.path = chat.app.path
        self.messages = chat.messages
        self.busy = False
        self.exit_after_busy = False
        # True ONLY in the delay between two requests (P19/WP-2). `busy` is True
        # only around a tool call, so without this flag `action_abort` takes its
        # cancel-and-delete branch during that sleep - and by then the attempt's
        # corpse is already rolled back, so `messages[-1]` is the USER message and
        # abort would delete the human's own turn.
        self.retrying = False
        prompt = self.prompt()
        endpoint = deepcopy(self.app.get_endpoint(self.cs("endpoint")))
        self.slot = -2
        model_settings = {}
        if self.cs("model_settings"):
            model_settings = self.settings.models[self.cs("model_settings")]
        tools_descs = []
        if self.cs("tools"):
            for _tool in self.app.tool_call.tools.keys():
                tool = self.app.tool_call.tools[_tool]
                if tool["desc"]["function"]["name"] in self.cs("tools") and self.req_mm_image(_tool):
                    tools_descs.append(tool["desc"])
        if self.local_server_active():
            address = f"http://127.0.0.1:{self.app.server.gets('server_port')}"
            api_key = self.app.server.api_key
            self.server_settings = self.app.server.get_server_settings(self.cs("model"))
        else:
            address = endpoint["endpoint_url"]["value"][:-3]
            api_key = endpoint["key"]
            self.server_settings = endpoint
        self.manage_cache = ManageCache(self.app, self.cs("endpoint"), self.server_settings, address, api_key)
        self.endpoint = LlamaCppEndpoint(self.messages, endpoint, self.cs("model"), model_settings, prompt,
                                         tools_descs, self.chat_view.callback)

    def req_mm_image(self, tool: dict) -> bool:
        if self.app.tool_call.tools[tool]["requires_multimodal_image"] and not self.chat.has_cap("image"):
            return False
        return True

    def prompt_inst(self, tool) -> str:
        prompt = ""
        if "prompt_inst" in self.app.tool_call.tools[tool]:
            prompt = self.app.tool_call.tools[tool]["prompt_inst"]
            for setting in self.app.tool_call.tools[tool]["settings"].keys():
                value = self.app.tool_call.tools[tool]["settings"][setting]["value"]
                if tool in self.settings.tool_settings:
                    if setting in self.settings.tool_settings[tool]:
                        value = self.settings.tool_settings[tool][setting]["value"]
                prompt = prompt.replace(f"[{setting}]", str(value))
        prompt = prompt.strip("\n")
        if prompt:
            return "\n" + prompt
        return ""

    def prompt(self) -> str:
        prompt = ""
        # The header belongs to the tool BLOCKS, not to the selection: a tool can be
        # selected and still drop out below (a multimodal tool on a chat without the
        # image capability), and then there is nothing to head. Emitting TOOL_PROMPT on
        # the strength of `cs("tools")` alone tells the model "All of your function
        # calls are rendered..." on a request whose payload carries no `tools` key at
        # all (unit:prompt t6 pins it; DECISIONS 62 owns the breaks of this prompt).
        blocks = []
        if self.cs("tools"):
            for tool in self.app.tool_call.tools.keys():
                if tool in self.cs("tools") and self.req_mm_image(tool):
                    tool_prompt = self.app.tool_call.tools[tool]["settings"]["prompt"]["value"]
                    if tool in self.settings.tool_settings:
                        if "prompt" in self.settings.tool_settings[tool]:
                            tool_prompt = self.settings.tool_settings[tool]["prompt"]["value"]
                    # work.py owns every break of the assembled prompt: a heading
                    # starts a line (else it is not a heading), the tool's text
                    # starts the line after it, the substituted instructions follow
                    # on the next line, and two tools are one blank line apart --
                    # so the newlines a stored or hand-written PROMPT happens to
                    # end with decide nothing.
                    text = tool_prompt.strip("\n")
                    block = f"## {tool}\n\n{text}" if text else f"## {tool}"
                    blocks.append(block + self.prompt_inst(tool))
        if blocks:
            prompt = TOOL_PROMPT + "\n\n".join(blocks)
        if self.cs("prompt") and self.cs("prompt") in self.settings.prompts:
            chat_prompt = self.settings.prompts[self.cs("prompt")]["text"]["value"]
            prompt =  "# INSTRUCTIONS\n\n" + chat_prompt + "\n\n" + prompt
        return prompt

    def local_server_active(self) -> bool:
        if self.cs("endpoint") == "0" and self.app.server.is_running():
            return True
        return False

    async def maybe_load_model(self) -> None:
        if self.local_server_active():
            await self.app.server.load_model(self.cs("model"))

    def save_cache_prompt(self) -> bool:
        if "save_cache_prompt" in self.server_settings:
            return self.server_settings["save_cache_prompt"]["value"]
        elif self.local_server_active():
            return self.app.server.gets("save_cache_prompt")
        return False

    async def before_work(self) -> None:
        if self.save_cache_prompt():
            self.slot = await self.manage_cache.get_slot(self.cs("model"), self.chat.id)
            self.endpoint.endpoint["slot_id"] = {"stype": "uinteger", "value": self.slot}

    async def after_work(self) -> None:
        # `slot >= 0` is the other half of the gate: -2 is "never took one" (the
        # gate above is then false anyway) and -1 is `get_slot_limited()`'s ANSWER
        # THAT THERE IS NO FREE SLOT - nothing was taken, so there is nothing to
        # hand back, and `slots[model][-1] = ...` would mark somebody ELSE'S slot
        # idle. The no-slot report is `work_stream`'s, where the question is asked.
        if self.save_cache_prompt() and self.slot >= 0:
            await self.manage_cache.return_slot(self.cs("model"), self.chat.id, self.slot)

    def harvest_usage(self) -> None:
        # The endpoint kept the last usage object of the stream that just ran, or
        # None when the server said nothing: silence must never zero what the chat
        # already knows, so this returns without touching the accumulated numbers.
        usage = self.endpoint.usage
        if not usage:
            return
        prompt = usage.get("prompt_tokens") or 0
        completion = usage.get("completion_tokens") or 0
        details = usage.get("prompt_tokens_details") or {}
        # `context` is the window fill of the LATEST call, never a sum: that call's
        # prompt already contains the previous answer and the tool results, so a
        # tool loop refreshes it instead of adding the history up again.
        self.chat.token_usage["context"] = prompt + completion
        # `generated` is the one number that does add up across the chat.
        self.chat.token_usage["generated"] += completion
        # Best effort: a server that sends no details leaves `cached` at 0 for this
        # read rather than keeping the count from the call before it.
        self.chat.token_usage["cached"] = details.get("cached_tokens") or 0

    async def work_stream(self) -> None:
        if "tool_calls" in self.messages[-1]:
            for tool_call in self.messages[-1]["tool_calls"]:
                self.busy = True
                await self.app.tool_call.call(self.messages, tool_call, self.chat.id, self.chat_view.callback)
                self.busy = False
                if self.exit_after_busy:
                    return None
        count = len(self.messages)
        await self.maybe_load_model()
        await self.before_work()
        if self.slot == -1:
            # The real answer to the question this file has asked since before P19
            # of the wrong object (`if self.endpoint == -1`, an object that is
            # never -1, so the branch was dead and the request went out carrying
            # `slot_id = -1`). -1 is `get_slot_limited()`'s reply when every
            # parallel slot is busy: no slot, no request, and nothing to return
            # below - `after_work` keeps that half.
            self.app.exception = Exception(
                "No free slot for inference available! Please try again later!")
            return None
        failure = None
        try:
            failure = await self.stream_attempts(count)
        finally:
            # The slot goes back on EVERY way out of the reply. The old code
            # `return`ed on the error path before `after_work()`, so the slot
            # `before_work()` took was never returned - with `parallel` set that
            # starves every other chat of a slot for the rest of the run. The gate
            # is `after_work`'s own (`save_cache_prompt`), so this finally costs
            # nothing on a chat that never took one.
            await self.after_work()
        if failure is not None:
            return None
        if "tool_calls" in self.messages[-1]:
            await self.work_stream()

    async def stream_attempts(self, count: int) -> Exception|None:
        """The ONE retry loop, around `endpoint.stream()` and nothing else.

        The width is the whole design (P19): `work_stream()` runs the tools BEFORE
        the request and recurses AFTER it, so a loop wrapped around anything wider
        would re-execute every tool call - files already written, commands already
        run - on each attempt. Here the second request is the only second thing.

        Answers None when a reply landed, or the failure that is reported. A
        non-`EndpointFailure` is NOT caught: it is a bug somewhere else and it
        re-raises out of the worker, past the `finally` above (which still returns
        the slot), exactly as it did before.

        `count` is the message length BEFORE the attempt: `stream()` appends the
        assistant dict and fires signal 1 BEFORE it asks, so a dead attempt leaves
        that dict behind, and after a half-streamed tool call a half-built
        `tool_calls` list. `remove_message_at` is awaited (not posted) because the
        next attempt must not start while the corpse still stands; it is the ONE
        rollback (the posted `RemoveMessage` handler is a thin caller of the same
        method), so the undo record, the widget, the window and the disk write all
        move together, once per attempt.
        """
        attempts = max(1, int(self.endpoint.attempts))
        for attempt in range(1, attempts + 1):
            try:
                # P13/WP-D: ask the hooks immediately before the request. The
                # position is load-bearing: this asks before EVERY request, the
                # retries included - and a note written now rides the payload
                # being built next (WP-A's unpacking). Nothing catches what a
                # hook raises: WP-B's contract, and the hook is total (unknown
                # figure => silence). attach() writes into the dicts; it adds no
                # item to self.messages, so it never disturbs the rollback below.
                self.chat.system_notes.attach()
                await self.endpoint.stream()
            except Exception as exception:
                if not isinstance(exception, EndpointFailure):
                    raise exception
                if not exception.retryable or attempt >= attempts:
                    return self.report_failure(exception, count)
                if len(self.messages) > count:
                    await self.chat_view.remove_message_at(len(self.messages) - 1)
                # The delay between two REQUESTS, in slices: an abort must end it
                # within about a tenth of a second, and `exit_after_busy` is the
                # flag abort sets on the branch `retrying` now selects.
                self.retrying = True
                try:
                    remaining = max(0.0, float(self.endpoint.delay))
                    while remaining > 0 and not self.exit_after_busy:
                        slice = min(0.1, remaining)
                        await asyncio.sleep(slice)
                        remaining -= slice
                finally:
                    self.retrying = False
                if self.exit_after_busy:
                    # Aborted: the human's own turn is the tail, the attempt's
                    # corpse is already gone, and NO FURTHER REQUEST is made.
                    return exception
        return None

    def report_failure(self, exception: Exception, count: int) -> Exception:
        # The same report the name-matching branch made, and by design the same
        # one a deterministic refusal gets on its FIRST attempt: the app shows it,
        # the attempt's dict is taken back, the model list is refreshed (a dead
        # endpoint may have lost its models). WP-4 turns the transient and
        # exhausted cases into an in-chat notice (DECISIONS 84 c); until then this
        # is the failure path, and it is reached once per reply, not per attempt.
        self.app.exception = exception
        if len(self.messages) > count:
            self.chat_view.post_message(RemoveMessage(len(self.messages)-1))
        self.chat.chat_settings.update_models()
        return exception
