from textual.widgets import TextArea

class TextAreaEdit(TextArea):
    def __init__(self, process, text: str):
        super().__init__()
        self.process = process
        self.chat_view = process.chat_view
        self.message = process.message
        self.chat = process.chat
        self.text = text
        self.old_text = text
        self.save_text = text
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
        if not self.styles.background == self._background:
            return None
        if not self.text == self.old_text:
            index = self.chat_view.messages.index(self.message.message)
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
        async with self.process.batch():
            await self.process.reset()
            await self.process.finish(self.save_text)
        self.message.is_edit -= 1
        self.process.is_edit = False
