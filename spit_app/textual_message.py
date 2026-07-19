from textual.message import Message

class DownloadFiles(Message):
    def __init__(self, sender_id: str, name: str, lst: list, callback: str) -> None:
        self.sender_id = sender_id
        self.name = name
        self.lst = lst
        self.callback = callback
        super().__init__()

class DownloadFailed(Message):
    def __init__(self, callback: str) -> None:
        self.callback = callback
        super().__init__()

class DownloadSuccess(Message):
    def __init__(self, callback: str) -> None:
        self.callback = callback
        super().__init__()
