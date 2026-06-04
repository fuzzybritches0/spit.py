from textual.events import DescendantFocus
from textual.widgets import Markdown
from textual.containers import VerticalScroll
from .content.content import Content
from .tool_calls import ToolCalls
from .actions import ActionsMixIn, bindings

class Message(ActionsMixIn, VerticalScroll):
    BINDINGS = bindings

    def __init__(self, chat, message: dict, display: bool = True) -> None:
        super().__init__()
        self.display = display
        self.message = message
        self.messages = chat.messages
        self.chat = chat
        self.role = self.message["role"]
        self.classes = "message-container-" + self.role
        self.id = "message-id-" + str(len(self.chat.chat_view.children))
        self.tc = ToolCalls(self)
        self.pr = {}
        self.processes = ["reasoning", "content", "tool_calls"]
        self.current_process = None
        self.finish_process = None

    async def update_status(self) -> None:
        if not self.current_process:
            return None
        if self.current_process == "reasoning":
            status = "Thinking..."
        else:
            status = ""
        if not self.status.source == status:
            await self.status.update(status)

    def get_update(self, process: str) -> tuple:
        if process in self.message and self.message[process]:
            if process == "tool_calls":
                self.tc.format_tool_calls()
                return "tool_calls", self.tc.parsed_tool_calls
            else:
                return process, self.message[process]
        else:
            return None, None

    def get_current_process(self) -> None:
        old_process = self.current_process
        for process in self.processes:
            if process in self.message and self.message[process]:
                self.current_process = process
        if not old_process == self.current_process:
            self.finish_process = old_process

    async def finish(self) -> None:
        await self.status.update("")
        for process in self.processes:
            proc, update = self.get_update(process)
            if proc:
                await self.maybe_mount_process(proc)
                await self.pr[proc].finish(update)

    async def process(self) -> None:
        if not self.has_focus and not self.has_focus_within:
            return None
        await self.update_status()
        self.get_current_process()
        await self.maybe_mount_process(self.current_process)
        if self.finish_process:
            proc, update = self.get_update(self.finish_process)
            await self.pr[proc].finish(update)
            self.finish_process = None
        proc, update = self.get_update(self.current_process)
        await self.pr[proc].process(update)

    async def reset(self) -> None:
        for process in self.pr.keys():
            await self.pr[process].remove()
        self.current_process = None
        self.finish_process = None
        self.tc = ToolCalls(self)
        self.pr = {}

    async def maybe_mount_process(self, process: str) -> None:
        if not process in self.pr:
            display = True
            if process == "reasoning":
                display = False
            self.pr[process] = Content(self.chat, self, process, display)
            await self.mount(self.pr[process])

    async def on_mount(self) -> None:
        self.status = Markdown()
        await self.mount(self.status)
        await self.status.update("Processing...")

    def on_focus(self) -> None:
        self.chat.chat_view.focused_message = self

    def on_descendant_focus(self, event: DescendantFocus) -> None:
        self.chat.chat_view.focused_message = event.control
