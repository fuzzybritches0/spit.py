from spit_app.chat.chat import Chat
from spit_app.modal_screens import InfoScreen 
from textual.widgets.option_list import Option

class ActionsMixIn:
    async def action_archive(self) -> None:
        if self.archive():
            await self.remove_children()
            await self.select_main_screen()

    async def action_unarchive(self) -> None:
        if self.unarchive():
            await self.remove_children()
            await self.select_main_screen()

    async def after_action(self, action: str) -> None:
        if action == "save" and self.new_manage:
            await self.remove()
            await self.app.query_one("#main").mount(Chat(f"chat-{self.uuid}"))
            await self.app.query_one("#side-panel").add_option_chat(f"chat-{self.uuid}")
        else:
            await super().after_action(action)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if self.children and self.children[0].id == "option-list":
            return False
        elif action == "cancel":
            if self.id == "new-chat":
                return False
        elif action == "save":
            if self.cur_dir == "chats_archive":
                return False
        elif action == "delete":
            if self.new_manage:
                return False
        elif action == "unarchive" and self.cur_dir == "chats":
            return False
        elif action == "archive" and (self.cur_dir == "chats_archive" or
                                      self.new_manage):
            return False
        return True

    async def on_extra_options(self, id) -> bool:
        if id == "select-new-manage" and not self.settings.endpoints:
            await self.app.push_screen(InfoScreen("No endpoints set! Please set up an endpoint first"))
            return True
        if id == "select-archive":
            self.cur_dir = "chats_archive"
            await super().after_action("")
            return True
        elif id == "select-leave-archive":
            self.cur_dir = "chats"
            await super().after_action("")
            return True
        return False

    def extra_options(self) -> list:
        Options = []
        if self.cur_dir == "chats":
            Options.append(Option(f"\nCreate new {self.id.split("-")[1]}\n", id="select-new-manage"))
            Options.append(Option("\nArchive\n", id="select-archive"))
        else:
            Options.append(Option("\nLeave archive\n", id="select-leave-archive"))
        return Options
