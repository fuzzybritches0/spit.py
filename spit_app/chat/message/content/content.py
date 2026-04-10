from .process.process import Process
from .image import Image
from textual.containers import Vertical

class Content(Vertical):
    def __init__(self, chat, message, scontent: str, display: bool = True) -> None:
        super().__init__()
        self.classes = "message-content"
        self.chat = chat
        self.message = message
        self.scontent = scontent
        self.display = display

    async def mount_parts(self, content: str|list) -> None:
        self.app.applog(content)
        if type(content) is str:
            if not self.children:
                await self.mount(Process(self.chat, self.message, self.scontent, 0))
        else:
            for part in range(len(self.children), len(content)):
                if content[part]["type"] == "text":
                    await self.mount(Process(self.chat, self.message, self.scontent, part))
                elif content[part]["type"] == "image_url":
                    await self.mount(Image())

    async def process(self, content: str|list) -> None:
        await self.mount_parts(content)
        if type(content) is str:
            await self.children[0].process(content)
        else:
            count = 0
            for part in self.children:
                if content[count]["type"] == "text":
                    await part.process(content[count]["text"])
                count+=1

    async def finish(self, content: str|list) -> None:
        await self.mount_parts(content)
        if type(content) is str:
            await self.children[0].finish(content)
        else:
            count = 0
            for part in self.children:
                if content[count]["type"] == "text":
                    await part.finish(content[count]["text"])
                elif content[count]["type"] == "image_url":
                    await part.finish(content[count]["image_url"]["url"])
                count+=1

    async def reset(self) -> None:
        await self.remove_children()
