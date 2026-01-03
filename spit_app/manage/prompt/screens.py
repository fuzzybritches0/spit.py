from textual.validation import Function
from textual.widgets import Button, OptionList, Label, Input, TextArea
from textual.widgets.option_list import Option
from textual.containers import Horizontal

class ScreensMixIn:
    async def select_main_screen(self) -> None:
        Options = [Option("\nCreate new System Prompt\n", id="select-new-prompt")]
        for prompt in self.settings.prompts.keys():
            name=self.settings.prompts[prompt]["name"]
            Options.append(Option(f"\nEdit: {name}\n", id=f"select-prompt-{prompt}"))
        await self.mount(OptionList(*Options, id="option-list"))
        self.children[0].focus()

    async def edit_prompt_screen(self) -> None:
        value = self.prompt["name"]
        await self.mount(Label("Name:"))
        await self.mount(Input(type="text", validators=[Function(self.is_not_empty)],
                                  id="name", value=value))
        text = self.prompt["text"]
        await self.mount(Label("Text:"))
        await self.mount(TextArea(text, id="text"))
        if self.new_prompt:
            await self.mount(Horizontal(
                Button("Save", id="save"),
                Button("Cancel", id="cancel"),
                id="save-delete-cancel"
            ))
        else:
            await self.mount(Horizontal(
                Button("Save", id="save"),
                Button("Delete", id="delete"),
                Button("Duplicate", id="duplicate"),
                Button("Cancel", id="cancel"),
                id="save-delete-cancel"
            ))
        self.children[1].focus()
