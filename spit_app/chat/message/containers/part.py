from textual.widgets import Markdown
from markdown_it import MarkdownIt

class Stream:
    def __init__(self, widget) -> None:
        self.widget = widget
        self.stream = Markdown.get_stream(widget)
        self.indent = None

    async def write(self, part: str) -> None:
        await self.stream.write(part)

    async def stop(self) -> None:
        await self.stream.stop()
        indent = 30
        for line in self.widget.source.split("\n"):
            if line:
                lline = line.lstrip(" ")
                ind = len(line) - len(lline)
                if indent > ind:
                    indent = ind
        self.widget.styles.margin = (0, 0, 0, indent)

class Part(Markdown):
    def __init__(self) -> None:
        super().__init__()
        self.app.refresh_bindings()

    def on_mount(self) -> None:
        self.stream = Stream(self)
        self.parent.target = self
