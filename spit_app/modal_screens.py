import os
from pathlib import Path
from textual.app import ComposeResult
from textual.widgets import Markdown, Button, Header, Footer, DirectoryTree
from textual.screen import ModalScreen
from textual.containers import Vertical, Horizontal, Center

class Common(ModalScreen):
    BINDINGS = [("ctrl+q", "exit_app", "Quit")]

    def action_exit_app(self) -> None:
        self.app.action_exit_app()

    def compose(self) -> ComposeResult:
        with Vertical(id=f"{self.mtype}-modal"):
            yield Markdown(self.text)
            if not self.mtype == "loading":
                with Center():
                    yield Button("OK")
        yield Footer()

class LoadingScreen(Common):
    def __init__(self) -> None:
        super().__init__()
        self.classes = "modal"
        self.mtype = "loading"
        self.text = "Loading ..."

class ErrorScreen(Common):
    def __init__(self, exception: Exception) -> None:
        super().__init__()
        self.classes = "modal"
        self.mtype = "error"
        self.text = f"# ERROR:\n\n- `{type(exception).__name__}` {exception}"

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()

class InfoScreen(Common):
    def __init__(self, info: str) -> None:
        super().__init__()
        self.classes = "modal"
        self.mtype = "info"
        self.text = f"INFO:\n\n{info}"

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()

class ConfirmScreen(Common):
    def __init__(self) -> None:
        super().__init__()
        self.classes = "modal"
        self.mtype = "confirm"

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.control.id == "ok":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def compose(self) -> ComposeResult:
        with Vertical(id=f"{self.mtype}-modal"):
            yield Markdown("# Are you sure?")
            with Horizontal():
                yield Button("CANCEL", id="cancel")
                yield Button("OK", id="ok")
        yield Footer()

class ChooseImageFile(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Dismiss"),
                ("ctrl+q", "exit_app", "Quit")]

    def __init__(self) -> None:
        super().__init__()
        self.classes = "modal"

    def action_exit_app(self) -> None:
        self.app.action_exit_app()

    def action_dismiss(self) -> None:
        self.dismiss(None)

    def on_directory_tree_file_selected(self, path: Path) -> None:
        self.dismiss(path)

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="choose-image-modal"):
            yield FilteredDirectoryTree("./")
        yield Footer()

class FilteredDirectoryTree(DirectoryTree):
    def is_image(self, path: str) -> bool:
        path = path.lower()
        exts = ["png", "jpeg", "jpg", "gif", "bmp", "tiff", "webp"]
        for ext in exts:
            if path.endswith(ext):
                return True
        return False

    def filter_paths(self, paths: list) -> list:
        ret = []
        for path in paths:
            if not path.name.startswith(".") and (os.path.isdir(path) or self.is_image(path.name)):
                ret.append(path)
        return ret
