from textual.widgets import Markdown
from textual.containers import VerticalScroll

class Code(VerticalScroll):
    BINDINGS = [
        ("y", "copy_to_clipboard", "Copy Code")
    ]

    def __init__(self) -> None:
        super().__init__()
        self.app.refresh_bindings()
        self.code = None

    def extract_code(self) -> None:
        code = self.children[0].source.strip()
        code = code.split("\n")
        self.first_line = code[0].strip()
        self.last_line = code[-1].strip()
        code = code[1:-1]
        eff_offset = len(code[0]) - len(code[0].lstrip(" "))
        if eff_offset > 0:
            for line in code:
                offset = len(line) - len(line.lstrip(" "))
                if line and offset < eff_offset:
                    eff_offset = offset
            offset_code = []
            for code_line in code:
                offset_code.append(code_line[eff_offset:])
            self.code = "\n".join(offset_code)
        else:
            self.code = "\n".join(code)

    async def update_code(self) -> None:
        if not self.code:
            self.extract_code()
        await self.children[0].update(self.first_line + "\n" + self.code + "\n" + self.last_line)

    def action_copy_to_clipboard(self) -> None:
        if not self.code:
            self.extract_code()
        self.app.copy_to_clipboard(self.code)

    def check_action(self, action: str,
                     parameters: tuple[object, ...]) -> bool | None:
        if self.parent.target is self:
            return False
        return True

    async def on_mount(self) -> None:
        self.classes = "code-listing-" + self.parent.parent.message["role"]
        await self.mount(Markdown())
        self.update = self.children[0].update
        self.append = self.children[0].append
        self.parent.target = self
