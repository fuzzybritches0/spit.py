from datetime import datetime
from textual.widgets import Select
from textual.widgets.option_list import Option
from spit_app.chat.chat import Chat

class ActionsMixIn:
    async def action_delete(self) -> None:
        self.delete()
        await self.remove_children()
        await self.select_main_screen()

    async def action_save(self) -> None:
        if self.valid_values():
            desc = self.query_one("#desc").value
            endpoint = self.query_one("#endpoint").value
            prompt = self.query_one("#prompt").value
            if prompt == Select.BLANK:
                prompt = None
            if self.cur_chat:
                self.update(desc, endpoint, prompt)
            else:
                self.new(desc, endpoint, prompt)
                await self.app.query_one("#main").mount(Chat(self.uuid))
                side_panel = self.app.query_one("#side-panel")
                await side_panel.option_selected(self.uuid)
                options = side_panel.options
                ctime = datetime.fromtimestamp(int(self.ctime))
                option = Option(f"{desc}\n{ctime}\n", id=self.uuid)
                new_options = options[0:1] + [option] + options[1:]
                side_panel.set_options(new_options)
                side_panel.highlighted = 1
            await self.remove_children()
            await self.select_main_screen()

    async def action_cancel(self) -> None:
        await self.remove_children()
        await self.select_main_screen()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if self.children and self.children[0].id == "option-list":
            return False
        if action == "delete" and not self.cur_chat:
            return False
        return True
