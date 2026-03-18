from .process.process import Process
from textual.containers import Vertical

class Content(Vertical):
    def __init__(self, message, scontent: str, display: bool = True) -> None:
        super().__init__()
        self.classes = "message-content"
        self.message = message
        self.scontent = scontent
        self.display = display

    async def mount_parts(self, content: str|list) -> None:
        if type(content) is str:
            parts = 1
        else:
            parts = len(content)
        count = 0
        for part in range(len(self.children), parts):
            await self.mount(Process(self.message, self.scontent, count))
            count+=1

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
                count+=1

    async def reset(self) -> None:
        await self.remove_children()
