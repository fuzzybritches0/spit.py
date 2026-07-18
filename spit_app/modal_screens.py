import os
from pathlib import Path
from textual.app import ComposeResult
from textual.message import Message
from textual.widgets import (Markdown, Button, Header, Footer, DirectoryTree,
                             Input, Button, Label, Rule, ProgressBar)
from textual.screen import ModalScreen
from textual.containers import Vertical, Horizontal, Center
from spit_app.manage.validation import ValidationMixIn

class ProgressDismiss(Message):
    ...

class CancelWork(Message):
    ...

class Common(ModalScreen):
    BINDINGS = [("ctrl+q", "exit_app", "Quit")]

    def action_exit_app(self) -> None:
        self.app.action_exit_app()

    def compose(self) -> ComposeResult:
        with Vertical(id=f"{self.mtype}-modal"):
            yield Markdown(self.text)
            with Center():
                yield Button("OK")
        yield Footer()

class ProgressBarScreen(ModalScreen):
    def __init__(self, download) -> None:
        super().__init__()
        self.classes = "modal"
        self.download = download

    def compose(self) -> ComposeResult:
        with Vertical(id="progress-bar-modal"):
            yield Label("", id="text")
            yield ProgressBar(id="progress-bar")
            with Horizontal(classes="auto-height"):
                yield Button("Dismiss", id="dismiss")
                yield Button("Cancel", id="cancel")
        yield Footer()

    def update_text(self, text: str) -> None:
        self.query_one("#text").update(text)

    def update_total(self, total: int) -> None:
        self.query_one("#progress-bar").update(total=total)

    def update_progress(self, advance: int) -> None:
        self.query_one("#progress-bar").advance(advance)

    def reset(self) -> None:
        self.query_one("#progress-bar").update(total=0, progress=0)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.control.id == "cancel":
            self.download.progress_state_reset()
            self.app.post_message(CancelWork())
        elif event.control.id == "dismiss":
            self.app.post_message(ProgressDismiss())

    def on_mount(self) -> None:
        self.update_text(self.download.progress_state["text"])
        self.update_total(self.download.progress_state["total"])
        self.update_progress(self.download.progress_state["progress"])

class LoadingScreen(ModalScreen):
    def __init__(self) -> None:
        super().__init__()
        self.classes = "modal"

    def compose(self) -> ComposeResult:
        with Vertical(id="loading-modal"):
            yield Markdown("Loading...")
        yield Footer()

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

class ChooseImageFile(ModalScreen, ValidationMixIn):
    BINDINGS = [("escape", "dismiss", "Dismiss"),
                ("ctrl+enter", "load_url", "Load image URL"),
                ("ctrl+q", "exit_app", "Quit")]

    def __init__(self) -> None:
        super().__init__()
        self.classes = "modal"
        self.manage = {"image_url": {"stype": "url", "empty": False, "desc": "Image URL"}}

    def action_exit_app(self) -> None:
        self.app.action_exit_app()

    def action_dismiss(self) -> None:
        self.dismiss(None)

    async def action_load_url(self) -> None:
        if await self.validate_values_edit():
            self.dismiss(self.query_one("#image_url").value)

    def on_directory_tree_file_selected(self, path: Path) -> None:
        self.dismiss(str(path.path))

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if await self.validate_values_edit():
            self.dismiss(self.query_one("#image_url").value)

    async def on_input_changed(self, event: Input.Changed) -> None:
        if event.validation_result:
            await self.update_val_results_input(event.control.id, event.validation_result.failure_descriptions)

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="choose-image-modal"):
            yield Label("Load image from URL (http:// or https://):")
            yield Input(id="image_url", validators=self.validators("image_url", "url"))
            yield Markdown(id="val-image_url")
            yield Button("Load", id="load-image-url")
            yield Rule()
            yield Label("Load local file:")
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
