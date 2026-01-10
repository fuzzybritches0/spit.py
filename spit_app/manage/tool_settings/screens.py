from textual.widgets import OptionList
from textual.widgets.option_list import Option

class ScreensMixIn:
    async def select_main_screen(self) -> None:
        Options = []
        for manage in self.managed.keys():
            Options.append(Option(f"\nEdit: {manage}\n", id=f"select-manage-{manage}"))
        await self.mount(OptionList(*Options, id="option-list"))
        self.children[0].focus()
