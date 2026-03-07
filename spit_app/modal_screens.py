from textual.app import ComposeResult
from textual.widgets import Markdown, Button, Footer
from textual.screen import ModalScreen
from textual.containers import Vertical, Horizontal, Center

class Common(ModalScreen):
    BINDINGS = [("ctrl+q", "exit_app", "Quit")]

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()

    def action_exit_app(self) -> None:
        self.app.action_exit_app()

    def compose(self) -> ComposeResult:
        with Vertical(id=f"{self.mtype}-modal"):
            yield Markdown(self.text)
            if not self.mtype == "loading":
                with Center():
                    yield Button("OK")
        yield Footer()

class LoadingScreen(Common):
    def __init__(self) -> None:
        super().__init__()
        self.classes = "modal"
        self.mtype = "loading"
        self.text = "Loading ..."

class ErrorScreen(Common):
    def __init__(self, exception: Exception) -> None:
        super().__init__()
        self.classes = "modal"
        self.mtype = "error"
        self.text = f"# ERROR:\n\n- `{type(exception).__name__}` {exception}"

class InfoScreen(Common):
    def __init__(self, info: str) -> None:
        super().__init__()
        self.classes = "modal"
        self.mtype = "info"
        self.text = f"INFO:\n\n{info}"

class ConfirmScreen(Common):
    def __init__(self) -> None:
        super().__init__()
        self.classes = "modal"
        self.mtype = "confirm"

    def compose(self) -> ComposeResult:
        with Vertical(id=f"{self.mtype}-modal"):
            yield Markdown("# Are you sure?")
            with Horizontal():
                yield Button("CANCEL", id="cancel")
                yield Button("OK", id="ok")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.control.id == "ok":
            self.dismiss(True)
        self.dismiss(False)
