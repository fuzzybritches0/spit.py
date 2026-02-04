import json
from textual.widgets import Markdown
from textual.containers import VerticalScroll
from .process import Process

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
        self.done_reasoning = False
        self.arguments = ""

    def tool_call_arguments(self, arguments: str) -> str:
        ret = ""
        if arguments.endswith("}"):
            arguments += ""
        elif (len(arguments) - len(arguments.replace('"', ""))) % 2 == 1:
            arguments += '"}'
        elif arguments.endswith(":"):
            arguments += '""}'
        elif arguments.endswith('"'):
            arguments += "}"
        try:
            arguments = json.loads(arguments)
        except:
            return self.arguments
        for argument in arguments.keys():
            ret +=f"\n    - {argument}:"
            if arguments[argument]:
                if type(arguments[argument]) is str and "\n" in arguments[argument]:
                    ret += f"\n```\n{arguments[argument]}\n```"
                else:
                    ret += f" `{arguments[argument]}`"
        self.arguments = ret
        return ret

    def format_tool_calls(self) -> str:
        tool_calls = "## TOOL CALLS\n"
        for tool_call in self.message["tool_calls"]:
            tool_calls += f"\n- function: `{tool_call['function']['name']}`\n  - arguments:\n"
            tool_calls += self.tool_call_arguments(tool_call["function"]["arguments"]) + "\n\n---"
        return tool_calls[:-5]

    async def update_status(self, status: str) -> None:
        if self.done_reasoning:
            return None
        if not self.status.source == status:
            await self.status.update(status)
        if not status:
            self.done_reasoning = True

    async def reset(self) -> None:
       await self.reasoning.reset()
       await self.content.reset()
       await self.tool_calls.reset()
       await self.process()
       await self.finish()

    async def finish(self) -> None:
        await self.update_status("")
        if "reasoning" in self.message:
            await self.reasoning.finish(self.message["reasoning"])
        if "content" in self.message:
            await self.content.finish(self.message["content"])
        if "tool_calls" in self.message:
            await self.tool_calls.process(self.format_tool_calls())
            await self.tool_calls.finish(self.format_tool_calls())

    async def process(self) -> None:
        if "reasoning" in self.message:
            await self.update_status("Thinking...")
            await self.reasoning.process(self.message["reasoning"])
        if "content" in self.message:
            if self.message["content"]:
                await self.update_status("")
            await self.content.process(self.message["content"])
        if "tool_calls" in self.message:
            if self.message["tool_calls"]:
                await self.update_status("")
            await self.tool_calls.process(self.format_tool_calls())

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
        self.reasoning = Process(False)
        await self.mount(self.reasoning)
        self.content = Process()
        await self.mount(self.content)
        self.tool_calls = Process()
        await self.mount(self.tool_calls)

    async def on_mount(self) -> None:
        await self.prepare()
        if self.chat.chat_view.has_focus_within:
            self.focus(scroll_visible=False)
        self.chat.chat_view.focused_message = self
