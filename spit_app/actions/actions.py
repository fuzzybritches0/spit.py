from spit_app.work import work_stream
import spit_app.message as message
import spit_app.utils as utils
from spit_app.config.config_app import ConfigScreen

class ActionsMixIn:
    def action_change_focus(self) -> None:
            self.text_area.focus()
    
    async def action_continue(self) -> None:
        if self.text_area.text:
            if self.state[-1]["role"] == "user":
                self.state[-1]["content"]+="\n\n"+self.text_area.text.strip("\n ")
            else:
                self.state.append({"role": "user", "content": self.text_area.text})
            utils.write_chat_history(self)
            await utils.render_message(self, "request", self.text_area.text)
            self.text_area.text = ""
        if (self.text_area.text or self.state[-1]["role"] == "user" or
            self.state[-1]["role"] == "tool" or self.state[-1]["tool_calls"]):
            self.work = self.run_worker(work_stream(self))
    
    async def action_abort(self) -> None:
        self.work.cancel()
        count_state = len(self.state)
        if self.state[0]["role"] == "system":
            count_state-=1
        while len(self.chat_view.children) > count_state:
            await message.remove_last_turn(self)
        self.refresh_bindings()
    
    async def action_remove_last_turn(self) -> None:
        utils.remove_last_message(self)
        await message.remove_last_turn(self)
        utils.write_chat_history(self)
        self.refresh_bindings()
    
    async def action_config_screen(self) -> None:
        await self.push_screen(ConfigScreen())
    
    async def action_exit_app(self) -> None:
        self.exit()
    
    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        running = False
        if self.work and self.work.is_running:
            running = True
        if action == "save_edit" or action == "cancel_edit":
            if self.edit:
                return True
            return False
        if action == "config_screen":
            if not running and not self.edit:
                return True
        if action == "continue":
            if self.edit:
                return False
            active = self.config.config["active_config"]
            if not running and self.config.config["configs"][active]["endpoint_url"]:
                if self.text_area.text and self.state[-1]["role"] == "system":
                    return True                                 # Begin of chat
                if (self.text_area.text and self.state[-1]["role"] == "assistant" and
                    self.state[-1]["content"]):
                    return True                                 # Normal turn
                if self.state[-1]["role"] == "user":
                    return True                                 # There is a user request
                if (self.state[-1]["role"] == "assistant" and
                    "tool_calls" in self.state[-1] and not self.text_area.text):
                    return True                                 # There are TOOL CALLS to call
                if self.state[-1]["role"] == "tool" and not self.text_area.text:
                    return True                                 # There are TOOL CALL results to process
            return False
        if action == "abort":
            if not running or self.edit:
                return False
        if action == "remove_last_turn":
            if running:
                return False
            if not self.state:
                return False
            if self.state[-1]["role"] == "system":
                return False
        if action.startswith("edit_"):
            if running:
                return False
            if self.focused == self.focused_message:
                id=int(self.focused.id[3:])
                if action == "edit_content":
                    if "content" in self.state[id]:
                        return True
                if action == "edit_cot":
                    if "reasoning_content" in self.state[id]:
                        return True
                if action == "edit_tool":
                    if "tool_calls" in self.state[id]:
                        return True
                return False
            else:
                return False
        return True
