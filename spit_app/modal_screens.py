from textual.app import ComposeResult
from textual.widgets import Static, Button, Footer
from textual.screen import ModalScreen
from textual.containers import Vertical, Center

class LoadingScreen(ModalScreen):
    def __init__(self) -> None:
        super().__init__()
        self.classes = "overlay"

    def compose(self) -> ComposeResult:
        with Vertical(id="loading-modal"):
            yield Static("Loading...")
        yield Footer()

class ErrorScreen(ModalScreen):
    BINDINGS = [("ctrl+q", "exit_app", "Quit")]

    def __init__(self, exception: Exception) -> None:
        super().__init__()
        self.classes = "overlay"
        self.exception = exception

    def compose(self) -> ComposeResult:
        with Vertical(id="error-modal"):
            exception = f"ERROR:\n\n{type(self.exception).__name__}: {self.exception}"
            yield Static(exception)
            with Center():
                yield Button("OK")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()

    def action_exit_app(self) -> None:
        self.app.action_exit_app()
