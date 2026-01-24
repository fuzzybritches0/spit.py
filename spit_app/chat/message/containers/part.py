from textual.widgets import Markdown

class Part(Markdown):
    def __init__(self) -> None:
        super().__init__()
        self.app.refresh_bindings()

    def on_mount(self) -> None:
        self.parent.target = self
