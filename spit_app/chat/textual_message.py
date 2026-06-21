from textual.message import Message

class StreamCallback(Message):
    def __init__(self, index: int, signal: int) -> None:
        self.signal = signal
        self.index = index
        super().__init__()

class RemoveMessage(Message):
    def __init__(self, index: int) -> None:
        self.index = index
        super().__init__()
