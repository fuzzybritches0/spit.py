from textual.app import ComposeResult
from textual.widgets import Static, Footer
from textual.containers import Container
from textual.screen import ModalScreen

class LoadingScreen(ModalScreen):
    CSS_PATH = "../styles/loading.css"

    def compose(self) -> ComposeResult:
        with Container(id="loading-indicator"):
            yield Static("Loading...")
        yield Footer()
