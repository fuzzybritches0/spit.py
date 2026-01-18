import json
from textual.containers import VerticalScroll
from .containers.part import Part
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
        self.focus(scroll_visible=False)
        self.thinking = False
        self.target = None
        self.pp = PatternProcessing(self)
        self.pos = 0
        self.content = ""

    async def reset(self) -> None:
        await self.remove_children()
        self.pp = PatternProcessing(self)
        self.pos = 0
        self.content = ""

    async def clean_after_thinking(self) -> None:
        if self.thinking:
            self.thinking = False
            await self.target.update("")

    async def process_content(self) -> None:
        self.pp.part = ""
        if len(self.content)-self.pos-self.pp.bsize > 0:
            for pos in range(self.pos, len(self.content) - self.pp.bsize):
                await self.pp.process_patterns(self.content[pos:])
            await self.target.append(self.pp.part)
            self.pos=pos+1

    async def finish(self) -> None:
        self.pp.part = ""
        for pos in range(self.pos, len(self.content)):
            await self.pp.process_patterns(self.content[pos:])
        await self.target.append(self.pp.part)

    async def process(self) -> None:
        if not self.target:
            await self.mount(Part())
        if "tool_calls" in self.message and self.message["tool_calls"][0]:
            await self.clean_after_thinking()
            self.content = json.dumps(self.message["tool_calls"])
        elif "content" in self.message and self.message["content"]:
            await self.clean_after_thinking()
            self.content = self.message["content"]
        elif "reasoning" in self.message and self.message["reasoning"]:
            if not self.thinking:
                await self.target.update("Thinking...")
                self.thinking = True
            return None
        if self.content:
            await self.process_content()

    def action_edit_content(self) -> None:
        self.edit_message("content")

    def action_edit_cot(self) -> None:
        self.edit_message("reasoning")

    def action_edit_tool(self) -> None:
        self.edit_message("tool_calls")

    def edit_message(self, ctype: str) -> None:
        self.chat.edit_role = self.message["role"]
        self.chat.text_area.temp = self.chat.text_area.text
        if ctype == "tool_calls" or self.chat.edit_role == "tool":
            self.chat.text_area.text = json.dumps(self.message[ctype])
        else:
            self.chat.text_area.text = self.message[ctype]
        self.chat.edit = True
        self.chat.edit_ctype = ctype
        self.chat.edit_container = self.app.focused
        self.chat.text_area.focus(scroll_visible=False)

    async def action_remove_last(self) -> None:
        self.chat.undo.append_undo("remove", self.message)
        del self.messages[-1]
        self.chat.write_chat_history()
        await self.remove()

    def check_action(self, action: str,
                     parameters: tuple[object, ...]) -> bool | None:
        if not self is self.app.focused:
            return False
        if self.chat.is_working() or self.chat.edit:
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
