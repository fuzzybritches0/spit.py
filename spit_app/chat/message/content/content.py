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
        if type(content) is str:
            if not self.children:
                await self.mount(Process(self.chat, self.message, self.scontent, 0))
        else:
            for part in range(len(self.children), len(content)):
                _type = content[part]["type"]
                if _type == "text" or _type == "function":
                    await self.mount(Process(self.chat, self.message, self.scontent, part))
                elif _type == "image_url":
                    await self.mount(Image())

    async def process(self, content: str|list) -> None:
        await self.mount_parts(content)
        if type(content) is str:
            await self.children[0].process(content)
        else:
            count = 0
            for part in self.children:
                _type = content[count]["type"]
                if _type == "text" or _type == "function":
                    await part.process(content[count][_type])
                count+=1

    async def finish(self, content: str|list) -> None:
        await self.mount_parts(content)
        if type(content) is str:
            await self.children[0].finish(content)
        else:
            count = 0
            for part in self.children:
                _type = content[count]["type"]
                if _type == "text" or _type == "function":
                    await part.finish(content[count][_type])
                elif _type == "image_url":
                    await part.finish(content[count][_type]["url"])
                count+=1
