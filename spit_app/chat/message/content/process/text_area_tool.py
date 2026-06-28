import json
from textual.widgets import TextArea, Markdown
from textual.containers import Vertical
from .tool_call import ToolCall

class TextAreaTool(Vertical):
    BINDINGS = [
        ("ctrl+enter", "save", "Save"),
        ("ctrl+escape", "cancel", "Cancel")
    ]

    def __init__(self, process, tool: dict):
        super().__init__()
        self.process = process
        self.chat_view = process.chat_view
        self.message = process.message
        self.chat = process.chat
        self.styles.height = "auto"
        self.tool = tool
        self.init()

    def init(self) -> None:
        self.old_tool = json.dumps(self.tool)
        self.arguments =  json.loads(self.tool["function"]["arguments"])
        self.tool_name = self.tool["function"]["name"]
        self.unknown_tool = True
        if self.tool_name in self.app.tool_call.tools:
            self.unknown_tool = False
            self.known_tool = self.app.tool_call.tools[self.tool_name]
            self.properties = self.known_tool["desc"]["function"]["parameters"]["properties"]

    async def on_mount(self) -> None:
        if self.unknown_tool:
            await self.mount(TextArea())
            self.children[0].styles.height = "auto"
            self.children[0].text = self.old_tool
            self.children[0].focus()
        else:
            await self.mount(Markdown(f"### function: `{self.tool_name}`\n#### arguments:"))
            for prop in self.properties.keys():
                value = ""
                if prop in self.arguments:
                    value = self.arguments[prop]
                await self.mount(Markdown(f"`{prop}`"))
                await self.mount(TextArea(id=prop))
                self.children[-1].text = value
                self.children[-1].styles.height = "auto"
            self.children[2].focus()

    def save_unknown(self) -> None:
        text = self.children[0].text
        if not text == self.old_tool:
            tool = None
            try:
                tool = json.loads(text)
            except:
                self.app.exception = Exception("no valid JSON!")
                return None
            if tool:
                self.message.message["tool_calls"][self.process.count] = tool

    def save_known(self) -> None:
        arguments = {}
        for prop in self.properties.keys():
            text = self.query_one(f"#{prop}").text
            if text:
                arguments[prop] = text
        arguments = json.dumps(arguments)
        self.message.message["tool_calls"][self.process.count]["function"]["arguments"] = arguments

    async def action_save(self) -> None:
        index = self.chat_view.messages.index(self.message.message)
        self.chat.undo.append_undo("change", self.message.message, index)
        if self.unknown_tool:
            self.save_unknown()
        else:
            self.save_known()
        self.chat.write_chat_history()
        await self.action_cancel()

    async def action_cancel(self) -> None:
        async with self.process.batch():
            await self.process.reset()
            tc = ToolCall(self.tool["function"])
            tc.format_tool_call()
            await self.process.finish(tc.formatted_tool_call)
        self.message.is_edit -= 1
        self.process.is_edit = False
