from textual.widgets import Button, OptionList
from textual.widgets.option_list import Option
from textual.containers import VerticalScroll, Horizontal
from .common import CommonMixIn
from .endpoint.main import Endpoints 
from .prompt.main import Prompts

class Main(CommonMixIn):
    CSS_PATH = "../styles/manage.css"
    BINDINGS = [
        ("escape", "dismiss", "Dismiss")
    ]

    async def select_main_screen(self) -> None:
        Options = [
                Option("\nManage Chats\n", id="manage-chats-screen"),
                Option("\nManage System Prompts\n", id="manage-prompts-screen"),
                Option("\nManage Endpoints\n", id="manage-endpoints-screen")
                ]
        vscroll = VerticalScroll(id="select-main")
        await self.dyn_container.mount(vscroll)
        await vscroll.mount(OptionList(*Options, id="main-option-list"))
        horiz = Horizontal(id="main-cancel-container")
        await vscroll.mount(horiz)
        await horiz.mount(Button("Cancel", id="cancel"))
        vscroll.children[0].focus()
        
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id == "manage-endpoints-screen":
            self.app.push_screen(Endpoints("Endpoints"))
        elif event.option.id == "manage-prompts-screen":
            self.app.push_screen(Prompts("System Prompts"))
