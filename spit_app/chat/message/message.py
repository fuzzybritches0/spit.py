import json
from textual.containers import VerticalScroll
from textual.widgets import Markdown
from .containers.part import Part
from .containers.code import Code
from .pattern_processing import PatternProcessing

class Message(VerticalScroll):
    BINDINGS = [
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
        self.id = "message-id-" + str(len(self.chat.chat_view.children))
        role = message["role"]
        if role == "tool":
            role = "user"
        self.classes = "message-container-" + role
        if (self.app.focused is self.app.query_one("#side-panel") or
            self.app.focused is self.chat.text_area):
            if not self.chat.is_working():
                self.focus(scroll_visible=False)
            else:
                self.chat.chat_view.focused_message = self
        else:
            if self.chat.display:
                self.focus(scroll_visible=False)
        self.chat.chat_view.focused_message = self
        self.reset_state()

    def reset_state(self) -> None:
        self.pp = PatternProcessing(self)
        self.pos = 0
        self.target = None
        self.lenreason = 0
        self.process_busy = False
        self.finish_pending = False
        self.finished_content = False

    async def reset(self) -> None:
        self.display = False
        await self.remove_children()
        self.reset_state()
        await self.process()
        await self.finish()
        self.display = True

    async def format_tool_calls(self) -> str:
        await self.tool_target.remove()
        for tool_call in self.message["tool_calls"]:
            content = "\n\n---\n\n"
            content += f"- function call: `{tool_call['function']['name']}`"
            content += f" id: `{tool_call['id']}`"
            await self.mount(Markdown(content))
            args = tool_call["function"]["arguments"]
            arguments = json.loads(args)
            for argument in arguments.keys():
                await self.mount(Markdown(f"\n- {argument}:"))
                await self.mount(Code(self.chat))
                await self.children[-1].update(f"```\n{arguments[argument]}\n```")
                await self.children[-1].update_code()
        return content

    async def process_tool_calls(self) -> None:
        content = json.dumps(self.message["tool_calls"])
        if len(content)-6 > 0:
            lensource = len(self.tool_target.source)
            await self.tool_target.append(content[lensource:-6])

    async def process_content(self) -> None:
        content = self.message["content"]
        self.pp.part = ""
        if len(content)-self.pos-self.pp.bsize > 0:
            for pos in range(self.pos, len(content) - self.pp.bsize):
                await self.pp.process_patterns(content[pos:])
            await self.target.append(self.pp.part)
            self.pos=pos+1

    async def finish_content(self) -> None:
        if self.finished_content:
            return None
        content = self.message["content"]
        self.pp.part = ""
        for pos in range(self.pos, len(content)):
            await self.pp.process_patterns(content[pos:])
        await self.target.append(self.pp.part)
        self.finished_content = True

    async def finish_tool_calls(self) -> None:
        if "tool_calls" in self.message and self.message["tool_calls"]:
            await self.format_tool_calls()

    async def finish(self) -> None:
        if self.process_busy:
            self.finish_pending = True
        else:
            self.finish_pending = False
            await self.finish_content()
            await self.finish_tool_calls()
            self.target = None

    async def process(self) -> None:
        if self.process_busy:
            return None
        self.process_busy = True
        if not self.target:
            await self.mount(Part(), before="#tool-calls")
        if "reasoning" in self.message and self.message["reasoning"]:
            lenreason = len(self.message["reasoning"])
            if lenreason > self.lenreason and not self.reasoning_target.source == "Thinking...":
                await self.reasoning_target.update("Thinking...")
                self.lenreason = lenreason
        if "content" in self.message and self.message["content"]:
            await self.reasoning_target.update("")
            await self.process_content()
        if "tool_calls" in self.message and self.message["tool_calls"]:
            await self.reasoning_target.update("")
            await self.finish_content()
            await self.process_tool_calls()
        self.process_busy = False
        if self.finish_pending:
            await self.finish()

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

    def check_action(self, action: str,
                     parameters: tuple[object, ...]) -> bool | None:
        if not self is self.app.focused:
            return False
        if self.chat.is_working() or self.chat.text_area.is_edit:
            return False
        match action:
            case "edit_content":
                if not self.message["content"]:
                    return False
            case "edit_cot":
                if not "reasoning" in self.message:
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

    def on_focus(self) -> None:
        self.chat.chat_view.focused_message = self

    async def on_mount(self) -> None:
        self.reasoning_target = Markdown()
        await self.mount(self.reasoning_target)
        await self.reasoning_target.update("Processing...")
        self.tool_target = Markdown(id="tool-calls")
        await self.mount(self.tool_target)
