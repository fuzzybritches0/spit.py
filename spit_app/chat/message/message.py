from textual.events import DescendantFocus
from textual.widgets import Markdown
from textual.containers import VerticalScroll
from .content.content import Content
from .actions import ActionsMixIn, bindings

class Message(ActionsMixIn, VerticalScroll):
    BINDINGS = bindings

    def __init__(self, chat, message: dict, display: bool = True) -> None:
        super().__init__()
        self.display = display
        self.message = message
        self.messages = chat.messages
        self.chat = chat
        self.chat_view = chat.chat_view
        self.text_area = chat.text_area
        self.role = self.message["role"]
        self.border_title = self.role
        self.classes = "message-container-" + self.role
        self.cnt = {}
        self.contents = ["reasoning", "content", "tool_calls"]
        self.current_content = None
        self.finish_content = None
        self.is_removing = False
        self.is_edit = 0

    async def update_status(self) -> None:
        if not self.current_content:
            return None
        if self.current_content == "reasoning":
            status = "Thinking..."
        else:
            status = ""
        if not self.status.source == status:
            await self.status.update(status)

    def get_update(self, content: str) -> tuple:
        if content in self.message and self.message[content]:
            return content, self.message[content]
        else:
            return None, None

    def is_message_type(self, content: str) -> bool:
        if not self.message[content]:
            return False
        _type = self.message[content][0]["type"]
        if self.message[content][0][_type]:
            return True
        return False

    def get_current_content(self) -> None:
        old_content = self.current_content
        for content in self.contents:
            if content in self.message:
                if ((type(self.message[content]) is str and self.message[content]) or
                    self.is_message_type(content)):
                    self.current_content = content
        if not old_content == self.current_content:
            self.finish_content = old_content

    async def finish(self) -> None:
        await self.status.update("")
        for content in self.contents:
            cont, update = self.get_update(content)
            if cont:
                await self.maybe_mount_content(cont)
                await self.cnt[cont].finish(update)

    async def process(self) -> None:
        await self.update_status()
        self.get_current_content()
        await self.maybe_mount_content(self.current_content)
        if self.finish_content:
            cont, update = self.get_update(self.finish_content)
            await self.cnt[cont].finish(update)
            self.finish_content = None
        cont, update = self.get_update(self.current_content)
        await self.cnt[cont].process(update)

    async def reset(self) -> None:
        for content in self.cnt.keys():
            await self.cnt[content].remove()
        self.current_content = None
        self.finish_content = None
        self.cnt = {}
        self.is_edit = 0

    async def maybe_mount_content(self, content: str) -> None:
        if not content in self.cnt:
            display = True
            if content == "reasoning" and not self.chat_view.is_edit:
                display = False
            self.cnt[content] = Content(self.chat, self, content, display)
            await self.mount(self.cnt[content])

    async def on_mount(self) -> None:
        self.status = Markdown()
        await self.mount(self.status)
        await self.status.update("Processing...")

    def on_focus(self) -> None:
        self.chat_view.focused_message = self
        self.chat_view.focused_widget = self

    def on_descendant_focus(self, event: DescendantFocus) -> None:
        self.chat_view.focused_message = self
        self.chat_view.focused_widget = event.widget
