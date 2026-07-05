from textual.widgets import TextArea
from spit_app.chat.textual_message import RemoveProcess

class TextAreaEdit(TextArea):
    def __init__(self, process, new: bool = False):
        super().__init__()
        self.new = new
        self.process = process
        self.message = process.message
        self.chat = process.chat
        if type(self.message.message[self.process.scontent]) is str:
            self.text = self.message.message[self.process.scontent]
        else:
            self.text = self.message.message[self.process.scontent][self.process.count]["text"]
        self.old_text = self.text
        self.save_text = self.text
        self.styles.height = "auto"
        self._background = self.styles.background

    def on_mount(self) -> None:
        self.focus()

    def on_text_area_changed(self) -> None:
        if not self.text:
            self.styles.background = "red"
        else:
            self.styles.background = self._background

    async def save(self) -> None:
        self.new = False
        if not self.styles.background == self._background:
            return None
        if not self.text == self.old_text:
            index = self.chat.message_index(self.message.message)
            self.chat.undo.append_undo("change", self.message.message, index)
            if type(self.message.message[self.process.scontent]) is str:
                self.message.message[self.process.scontent] = self.text
            else:
                self.message.message[self.process.scontent][self.process.count]["text"] = self.text
            self.chat.write_chat_history()
            self.save_text = self.text
        else:
            self.save_text = self.old_text
        await self.cancel()

    async def cancel(self) -> None:
        if self.new:
            self.message.post_message(RemoveProcess(self.process.scontent, self.process.count))
            return None
        async with self.process.batch():
            await self.process.reset()
            await self.process.finish(self.save_text)
        self.message.is_edit -= 1
        self.process.is_edit = False
