# SPDX-License-Identifier: GPL-2.0
import asyncio
from textual import work
from textual.events import Focus
from textual.containers import Horizontal
from textual.widgets import Label, Select
from spit_app.endpoints.llamacpp import get_models, get_model_capabilities, get_models_tuple, get_models_list, get_context_size

DASH = "—"

def count_or_dash(value: int|None) -> str:
    # A count the app does not have is a dash: never a number, and never 0. The
    # limit in this row is the only place a chat can overflow and the user is
    # told about it, so an invented figure there is a lie about when the chat
    # dies — which is why get_context_size() answers None rather than guessing
    # (P12 step 1). 0 renders as 0 when a server really did report 0.
    if value is None:
        return DASH
    return str(value)

class ChatSettings(Horizontal):
    BINDINGS = [("ctrl+s", "leave_settings", "Leave settings")]

    def __init__(self, chat) -> None:
        super().__init__()
        self.id = "chat-settings"
        self.chat = chat
        self.cs = chat.cs
        self.settings = chat.settings
        self.selects = [ 1, 3, 5]
        self.models = []
        # How large the window the server runs is, per (endpoint, model) this row
        # points at: an absent key was never asked, None was asked and the server
        # would not say. Keyed by the pair so ONE pair costs the two GETs of
        # get_context_size() once, not once per reply.
        self.context_sizes = {}
        # The counts row itself. Created and mounted LAST in on_mount, and that
        # position is load-bearing — see the note there.
        self.usage_label = None

    async def on_select_changed(self, event: Select.Changed) -> None:
        if event.value == "none":
            return None
        if event.control.id == "select-endpoint":
            self.cs("endpoint", event.value)
            self.update_models()
        if event.control.id == "select-model":
            self.cs("model", event.value)
            self.chat.model_capabilities = get_model_capabilities(self.models, self.cs("model"))
        if event.control.id == "select-model-settings":
            if event.value == Select.NULL:
                self.cs("model_settings", None)
            else:
                self.cs("model_settings", event.value)
        self.chat.write_chat_history()
        # The endpoint and the model are what the counts row is built from, and
        # this is the only place either of them changes: on_select_changed is also
        # the change notification for a model set programmatically (Select posts
        # Changed for a value assignment, so the model update_models() picks lands
        # here too). It fires for model_settings as well, which is not in the
        # cache key: that costs one redraw and no probe.
        self.refresh_usage()

    def on_focus(self, event: Focus) -> None:
        event.prevent_default()
        self.children[self.selects[0]].focus()

    def allowed_focus(self) -> None:
        for select in self.selects:
            self.children[select].can_focus = True

    def disallowed_focus(self) -> None:
        for select in self.selects:
            self.children[select].can_focus = False

    def set_value(self, options: tuple, option: str, allow_blank: bool) -> str:
        if not option or not option in (i for n, i in options):
            if allow_blank:
                return Select.NULL
            else:
                return options[0][1]
        return option

    def action_leave_settings(self) -> None:
        self.chat.focus()

    async def on_mount(self) -> None:
        options = (("None", "none"),)
        await self.mount(Label("Endpoint:"))
        await self.mount(Select(options, id="select-endpoint", allow_blank=False, compact=True))
        await self.mount(Label("Model:"))
        await self.mount(Select(options, id="select-model", allow_blank=False, compact=True))
        await self.mount(Label("Settings:"))
        await self.mount(Select(options, id="select-model-settings", allow_blank=True, compact=True))
        # LAST, deliberately: self.selects and every children[1/3/5] in this file
        # index BY POSITION, so a widget mounted before the Selects shifts them
        # all and chat_smoke dies on `'Label' object has no attribute
        # 'set_options'` — which the runner's `| tail -n 1` reports as
        # PASS: 0 FAIL: 0, i.e. a suite that cannot even report itself (measured,
        # P12 step 4). Appended after the Selects nothing moves.
        self.usage_label = Label(self.usage_text())
        await self.mount(self.usage_label)
        self.update_selects()
        self.disallowed_focus()

    def context_key(self) -> tuple:
        # The (endpoint, model) pair the window size belongs to. "none" is the
        # placeholder this row's own model Select carries while the endpoint has
        # no models, and NULL/None is the unselected state: asking a router-mode
        # server for "?model=none" can refuse the very answer the probe came for,
        # so the placeholders ask the unqualified question, and every spelling of
        # "no model" shares one cache entry.
        model = self.cs("model")
        if not model or model == "none":
            model = None
        return (self.cs("endpoint"), model)

    def usage_text(self) -> str:
        usage = self.chat.token_usage
        return (f"ctx {count_or_dash(usage.get('context'))} / "
                f"{count_or_dash(self.context_sizes.get(self.context_key()))}"
                f" · gen {count_or_dash(usage.get('generated'))}"
                f" · cached {count_or_dash(usage.get('cached'))}")

    def refresh_usage(self) -> None:
        # Public seam: redraw the counts row from what is already known.
        #
        # Called from exactly two places: the signal-0 branch of
        # ChatView.on_stream_callback (the end of every reply, callback.py) and
        # on_select_changed (the endpoint or model moved). Never from a handler on
        # THIS widget for the stream: a StreamCallback is posted on the chat_view
        # and a Textual Message bubbles to ANCESTORS only, so ChatSettings — a
        # SIBLING of the ChatView under Chat — is never delivered one. A handler
        # here for signal 0 would sit dead and invisible to every suite in the
        # repo (measured 2026-09-22: the receivers are ChatView and Chat).
        #
        # Nothing here touches the network. token_usage is already on the Chat —
        # Work.harvest_usage() fills it when stream() returns, and this signal is
        # the last thing stream() posts, so it is delivered after the harvest and
        # the row shows THIS reply's numbers, not the previous one's (verified,
        # not assumed). The window size is the one number that needs a question,
        # and it goes to a worker.
        if self.usage_label is None:
            return None
        self.usage_label.update(self.usage_text())
        key = self.context_key()
        if key in self.context_sizes:
            return None
        if not key[0] in self.app.endpoint_list():
            return None
        self.probe_context_size(key)

    @work(group="context-size", exclusive=True, exit_on_error=False)
    async def probe_context_size(self, key: tuple) -> None:
        # get_context_size() is two HTTP GETs with timeout=3 each
        # (llamacpp.py:42-53), so on an endpoint that answers neither route it is
        # ~6 s: a worker, never inline in a signal handler, because 6 s on the end
        # of every reply is a frozen UI and the golden has no word for either.
        #
        # Its OWN group because exclusive with the DEFAULT group cancels every
        # other worker of this widget — update_models() included, which loops up
        # to 60 times waiting for a server to come up (measured 2026-09-22). This
        # way a rapid endpoint switch replaces the probe in flight and nothing
        # else is touched.
        #
        # Guarded the way update_models() guards: an id that is not in the
        # endpoint list has no endpoint to ask, and that is what keeps
        # get_context_size() away from the {} an app stub answers with (it raises
        # KeyError on a missing endpoint_url, llamacpp.py:37).
        if not key[0] in self.app.endpoint_list():
            return None
        size = await get_context_size(self.app.get_endpoint(key[0]), key[1])
        # Stored under the pair this probe was started for, not the one that is
        # selected now: the answer belongs to the endpoint that was asked. The
        # redraw below reads the CURRENT pair, so a late answer can never be shown
        # against an endpoint it does not describe.
        self.context_sizes[key] = size
        if self.usage_label is not None:
            self.usage_label.update(self.usage_text())

    @work(exclusive=True, exit_on_error=False)
    async def update_models(self) -> None:
        self.children[3].set_options((("None", "none"),))
        count = 0
        while True:
            capabilities = self.chat.model_capabilities
            if not self.cs("endpoint") in self.app.endpoint_list():
                return None
            endpoint = self.app.get_endpoint(self.cs("endpoint"))
            self.models = await get_models(endpoint)
            if self.models:
                options = get_models_tuple(self.models)
                self.children[3].set_options(options)
                if self.cs("model") in get_models_list(self.models):
                    self.children[3].value = self.cs("model")
                self.cs("model", self.children[3].value)
                self.chat.write_chat_history()
                self.chat.model_capabilities = get_model_capabilities(self.models, self.cs("model"))
                if not capabilities == self.chat.model_capabilities:
                    self.chat.refresh_bindings()
                return None
            else:
                count += 1
                if count > 60:
                    return None
                await asyncio.sleep(10)

    def update_selects(self) -> None:
        options = self.get_options()
        self.children[1].set_options(options[0])
        self.children[5].set_options(options[1])
        self.set_selects(options)
        self.update_models()

    def get_options(self) -> list:
        options = []
        options.append(self.app.endpoint_list_tuple())
        options.append(self.model_settings_options())
        return options

    def set_selects(self, options: list) -> None:
        self.children[1].value = self.set_value(options[0], self.cs("endpoint"), False)
        self.cs("endpoint", self.children[1].selection)
        self.children[5].value = self.set_value(options[1], self.cs("model_settings"), True)
        self.cs("model_settings", self.children[5].selection)
        self.chat.write_chat_history()

    async def on_descendant_focus(self) -> None:
        self.allowed_focus()

    def on_descendant_blur(self) -> None:
        if not self.has_focus_within:
            self.disallowed_focus()

    def model_settings_options(self) -> None:
        tup = ()
        for key in self.settings.models.keys():
            tup += ((self.settings.models[key]["name"]["value"], key),)
        return tup
