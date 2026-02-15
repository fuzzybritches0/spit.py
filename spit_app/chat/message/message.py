import json
from textual.widgets import Markdown
from textual.containers import VerticalScroll
from .process import Process
from .tool_calls import ToolCalls

class Message(VerticalScroll):
    BINDINGS = [
        ("s", "show_cot", "Show CoT"),
        ("s", "hide_cot", "Hide CoT"),
        ("e", "edit_content", "Edit content"),
        ("c", "edit_cot", "Edit CoT"),
        ("t", "edit_tool", "Edit tool call"),
        ("x", "remove_last", "Remove turn")
    ]

    def __init__(self, chat, message) -> None:
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
            status = "Thinking"
        else:
            status = ""
        if not self.status.source == status:
            await self.status.update(status)

    def get_current_process(self) -> None:
        old_process = self.current_process
        for process in self.processes:
            if process in self.message and self.message[process]:
                self.current_process = process
        if not old_process == self.current_process:
            self.finish_process = old_process

    def get_update(self, process: str) -> tuple:
        if process in self.message and self.message[process]:
            if process == "tool_calls":
                self.tc.format_tool_calls()
                return self.pr["tool_calls"], self.tc.parsed_tool_calls
            else:
                return self.pr[process], self.message[process]
        else:
            return None, None

    async def reset(self) -> None:
        await self.pr["reasoning"].reset()
        await self.pr["content"].reset()
        await self.pr["tool_calls"].reset()
        self.current_process = None
        self.finish_process = None
        self.tc = ToolCalls(self)
        await self.finish()

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

    def action_show_cot(self) -> None:
        self.reasoning.display = True
        self.reasoning.disabled = False
        self.app.refresh_bindings()

    def action_hide_cot(self) -> None:
        self.reasoning.display = False
        self.reasoning.disabled = True
        self.app.refresh_bindings()

    def action_edit_content(self) -> None:
        self.edit_message("content")

    def action_edit_cot(self) -> None:
        self.edit_message("reasoning")

    def action_edit_tool(self) -> None:
        self.edit_message("tool_calls")

    def edit_message(self, ctype: str) -> None:
        self.chat.text_area.temp = self.chat.text_area.text
        if ctype == "tool_calls":
            self.chat.text_area.text = json.dumps(self.message[ctype])
        else:
            self.chat.text_area.text = self.message[ctype]
        self.chat.text_area.is_edit = True
        self.chat.text_area.ctype = ctype
        self.chat.text_area.edit_container = self
        self.chat.text_area.focus()

    async def action_remove_last(self) -> None:
        self.chat.undo.append_undo("remove", self.message)
        del self.messages[-1]
        self.chat.write_chat_history()
        await self.remove()

    def has_reasoning(self) -> bool:
        if self.message["role"] == "assistant" and self.message["reasoning"]:
            return True
        return False

    def check_action(self, action: str,
                     parameters: tuple[object, ...]) -> bool | None:
        if not self is self.app.focused:
            return False
        if self.chat.is_working() or self.chat.text_area.is_edit:
            return False
        match action:
            case "show_cot":
                if not self.has_reasoning():
                    return False
                if self.reasoning.display:
                    return False
            case "hide_cot":
                if not self.has_reasoning():
                    return False
                if not self.reasoning.display:
                    return False
            case "edit_content":
                if not self.message["content"]:
                    return False
            case "edit_cot":
                if not self.has_reasoning():
                    return False
            case "edit_tool":
                if not "tool_calls" in self.message:
                    return False
            case "remove_last":
                if not self.parent.children:
                    return False
                if not self is self.parent.children[-1]:
                    return False
        return True

    async def prepare(self) -> None:
        self.status = Markdown()
        await self.mount(self.status)
        await self.status.update("Processing...")
        self.pr["reasoning"] = Process(False)
        await self.mount(self.pr["reasoning"])
        self.pr["content"] = Process()
        await self.mount(self.pr["content"])
        self.pr["tool_calls"] = Process()
        await self.mount(self.pr["tool_calls"])

    async def on_mount(self) -> None:
        await self.prepare()
        if self.chat.chat_view.has_focus_within:
            self.focus(scroll_visible=False)
        self.chat.chat_view.focused_message = self
