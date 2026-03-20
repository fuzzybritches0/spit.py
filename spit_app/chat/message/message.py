from textual.widgets import Markdown
from textual.containers import VerticalScroll
from .content.content import Content
from .tool_calls import ToolCalls
from .actions import ActionsMixIn, bindings

class Message(ActionsMixIn, VerticalScroll):
    BINDINGS = bindings

    def __init__(self, chat, message: dict) -> None:
        super().__init__()
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
                return self.pr["tool_calls"], self.tc.parsed_tool_calls
            else:
                return self.pr[process], self.message[process]
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
                await proc.finish(update)

    async def process(self) -> None:
        await self.update_status()
        self.get_current_process()
        if self.finish_process:
            proc, update = self.get_update(self.finish_process)
            await proc.finish(update)
            self.finish_process = None
        proc, update = self.get_update(self.current_process)
        await proc.process(update)

    async def reset(self) -> None:
        await self.pr["reasoning"].reset()
        await self.pr["content"].reset()
        await self.pr["tool_calls"].reset()
        self.current_process = None
        self.finish_process = None
        self.tc = ToolCalls(self)
        await self.finish()

    async def prepare(self) -> None:
        self.status = Markdown()
        await self.mount(self.status)
        await self.status.update("Processing...")
        self.pr["reasoning"] = Content(self.chat, self, "reasoning", False)
        await self.mount(self.pr["reasoning"])
        self.pr["content"] = Content(self.chat, self, "content")
        await self.mount(self.pr["content"])
        self.pr["tool_calls"] = Content(self.chat, self, "tool_calls")
        await self.mount(self.pr["tool_calls"])

    async def on_mount(self) -> None:
        await self.prepare()
        if self.chat.chat_view.has_focus_within:
            self.focus(scroll_visible=False)
        self.chat.chat_view.focused_message = self
