from textual.widgets import Markdown
from markdown_it import MarkdownIt

def parser_factory() -> MarkdownIt:
    return MarkdownIt("gfm-like").disable(["code", "html_inline"])

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
                    if indent == 0:
                        break
        if indent > 0:
            self.widget.styles.margin = (0, 0, 0, indent)

class Part(Markdown):
    def __init__(self) -> None:
        super().__init__(parser_factory=parser_factory)
        self.app.refresh_bindings()

    def on_mount(self) -> None:
        self.stream = Stream(self)
        self.parent.target = self
