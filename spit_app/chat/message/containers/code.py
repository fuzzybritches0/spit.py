from textual.widgets import Markdown
from textual.containers import VerticalScroll

class Code(VerticalScroll):
    BINDINGS = [
        ("y", "copy_to_clipboard", "Copy Code")
    ]

    def __init__(self) -> None:
        super().__init__()
        self.code = None
        self.focus(scroll_visible=False)

    async def update(self, source: str) -> None:
        await self.children[0].update(source)

    async def append(self, part: str) -> None:
        await self.children[0].append(part)

    def extract_code(self) -> None:
        code = self.children[0].source
        code = code.split("\n", 1)
        self.first_line = code[0]
        code = code[1]
        code = code.split("\n")
        offset = len(code[0]) - len(code[0].lstrip(" "))
        offset_code = []
        for code_line in code:
            offset_code.append(code_line[offset:])
        self.code = "\n".join(offset_code)

    async def update_code(self) -> None:
        if not self.code:
            self.extract_code()
        fence = self.first_line
        while not fence[-1] == fence[1]:
            fence = fence[:-1]
        await self.children[0].update(self.first_line + "\n" + self.code + "\n" + fence)

    def action_copy_to_clipboard(self) -> None:
        if not self.code:
            self.extract_code()
        self.app.copy_to_clipboard(self.code)

    async def on_mount(self) -> None:
        self.classes = "code-listing-" + self.parent.message['role']
        await self.mount(Markdown())
        self.parent.target = self
