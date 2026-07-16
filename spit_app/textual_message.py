from textual.message import Message

class DownloadFiles(Message):
    def __init__(self, sender, lst: list, callback: str) -> None:
        self.sender = sender
        self.lst = lst
        self.callback = callback
        super().__init__()

class DownloadFailed(Message):
    def __init__(self, lst: list, callback: str) -> None:
        self.lst = lst
        self.callback = callback
        super().__init__()

class DownloadSuccess(Message):
    def __init__(self, lst: list, callback: str) -> None:
        self.lst = lst
        self.callback = callback
        super().__init__()
