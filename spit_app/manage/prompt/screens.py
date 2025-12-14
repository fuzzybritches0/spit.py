from textual.validation import Function
from textual.widgets import Button, OptionList, Label, Input, TextArea
from textual.widgets.option_list import Option
from textual.containers import VerticalScroll, Horizontal

class ScreensMixIn:
    async def select_main_screen(self) -> None:
        vscroll = VerticalScroll(id="select-main")
        await self.dyn_container.mount(vscroll)
        Options = [ Option("\nCreate new System Prompt\n", id="select-new-prompt") ]
        for prompt in self.settings.system_prompts.keys():
            name=self.settings.system_prompts[prompt]["name"]
            Options.append(Option(f"\nEdit: {name}\n", id=f"select-prompt-{prompt}"))
        await vscroll.mount(OptionList(*Options, id="option-list"))
        horiz = Horizontal(id="cancel-container")
        await self.dyn_container.mount(horiz)
        await horiz.mount(Button("Cancel", id="cancel"))
        vscroll.children[0].focus()

    async def edit_prompt_screen(self) -> None:
        vscroll = VerticalScroll(id="edit-prompt")
        await self.dyn_container.mount(vscroll)
        value = self.settings.system_prompts[self.cur_system_prompt]["name"]
        await vscroll.mount(Label("Name:"))
        await vscroll.mount(Input(type="text", validators=[Function(self.val.is_not_empty)],
                                  id="name", value=value))
        text = self.settings.system_prompts[self.cur_system_prompt]["text"]
        await vscroll.mount(Label("Text:"))
        await vscroll.mount(TextArea(text, id="text"))
        horiz = Horizontal(id="save-delete-cancel")
        await self.dyn_container.mount(horiz)
        await horiz.mount(Button("Save", id="save"))
        await horiz.mount(Button("Delete", id="delete"))
        await horiz.mount(Button("Cancel", id="cancel"))
        vscroll.children[1].focus()
