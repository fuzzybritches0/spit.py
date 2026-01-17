from textual.widgets import Markdown

class Part(Markdown):
    def __init__(self) -> None:
        super().__init__()

    def on_mount(self) -> None:
        self.parent.target = self
        self.parent.focus(scroll_visible=False)
