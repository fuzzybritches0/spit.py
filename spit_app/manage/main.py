from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, OptionList, Header, Footer
from textual.widgets.option_list import Option
from textual.containers import VerticalScroll, Horizontal
from .validation import Validation
from .endpoint.actions import ActionsMixIn as EndpointActions
from .endpoint.handlers import HandlersMixIn as EndpointHandlers
from .endpoint.screens import ScreensMixIn as EndpointScreens
from .endpoint.validation import ValidationMixIn as EndpointValidations

class CommonMixIn:
    async def clean_dyn_container(self) -> None:
        await self.dyn_container.remove_children()

class Endpoints(CommonMixIn, EndpointActions,
                EndpointHandlers, EndpointScreens,
                EndpointValidations, ModalScreen): 
    CSS_PATH = "../styles/manage.css"
    BINDINGS = [
        ("ctrl+enter", "save", "Save"),
        ("ctrl+r", "delete", "Delete"),
        ("ctrl+s", "set_active", "Set active"),
        ("escape", "dismiss", "Cancel")
    ]

    def __init__(self) -> None:
        super().__init__()
        self.settings = self.app.settings
        self.val = Validation(self)

    def update_title(self, section) -> None:
        self.title = f"{self.app.NAME} v{self.app.VERSION} - Manage - Endpoints"

    def compose(self) -> ComposeResult:
        yield Header()
        self.dyn_container = VerticalScroll()
        yield self.dyn_container
        yield Footer()

    async def on_mount(self) -> None:
        await self.select_endpoint_screen()

class Main(ModalScreen):
    CSS_PATH = "../styles/manage.css"
    BINDINGS = [
        ("escape", "dismiss", "Dismiss")
    ]

    def __init__(self) -> None:
        super().__init__()

    def update_title(self, section) -> None:
        self.title = f"{self.app.NAME} v{self.app.VERSION} - Manage - Main"

    def compose(self) -> ComposeResult:
        yield Header()
        for each in self.select_main_screen():
            yield each
        yield Footer()

    def select_main_screen(self) -> None:
        Options = [
                Option("\nManage Chats\n", id="manage-chats-screen"),
                Option("\nManage System Prompts\n", id="manage-prompts-screen"),
                Option("\nManage Endpoints\n", id="manage-endpoints-screen")
                ]
        with VerticalScroll(id="select-main"):
            yield OptionList(*Options, id="main-option-list")
            with Horizontal(id="main-cancel-container"):
                yield Button("Cancel", id="cancel")
        
    async def on_mount(self) -> None:
        self.query_one("#main-option-list").focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id == "manage-endpoints-screen":
            self.app.push_screen(Endpoints())
