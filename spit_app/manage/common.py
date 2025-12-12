from textual.app import ComposeResult
from textual.widgets import Header, Footer
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from .validation import Validation

class CommonMixIn(ModalScreen):
    def __init__(self, module) -> None:
        super().__init__()
        self.settings = self.app.settings
        self.update_title(module)
        self.val = Validation(self)

    def compose(self) -> ComposeResult:
        yield Header()
        self.dyn_container = VerticalScroll()
        yield self.dyn_container
        yield Footer()

    async def on_mount(self) -> None:
        await self.select_main_screen()

    def update_title(self, section) -> None:
        self.title = f"{self.app.NAME} v{self.app.VERSION} - Manage - {section}"

    async def clean_dyn_container(self) -> None:
        await self.dyn_container.remove_children()
