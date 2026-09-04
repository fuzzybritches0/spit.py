# SPDX-License-Identifier: GPL-2.0
"""Fake Textual (and friends) so the render pipeline can be driven headless.

The modules under test - Process, PatternProcessing, pattern_methods and the
Part/Code/LaTeX containers - import Textual at module load. The system
python3 has no Textual (TRAPS #19) and the tests must run without the app,
so this file injects minimal stand-ins into sys.modules BEFORE those
modules are imported. Only the surface the pipeline actually touches is
implemented:

- a widget base class whose mount() records the tree and calls on_mount
  (Textual mounts synchronously enough for await mount() to land the
  widget and run its on_mount before returning);
- Markdown with a class-level get_stream() returning a stream that appends
  to the widget's source, so "what is on screen" is the ordered list of
  final sources of the mounted widgets;
- LaTeX's heavy imports (cairosvg, ziamath, PIL, textual_image) as empty
  stand-ins - LaTeX is imported by pattern_methods even when no fixture
  contains latex, and is never instantiated by these tests.

Everything in the modules under test runs for real: only the widget
backbone is faked.
"""
import inspect
import sys
import types


def _module(name):
    mod = sys.modules.get(name)
    if mod is None:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
    return mod


class FakeStyles:
    def __init__(self):
        self.margin = None
        self.height = None
        self.width = None
        self.color = types.SimpleNamespace(css="#000000")
        self.background = types.SimpleNamespace(css="#000000")


class FakeMessage:
    def __init__(self, *args, **kwargs):
        pass


class FakeStream:
    def __init__(self, widget):
        self.widget = widget
        self.stopped = False

    async def write(self, part):
        if part:
            self.widget.source += part

    async def stop(self):
        self.stopped = True


class FakeMarkdown:
    def __init__(self, source="", parser_factory=None, **kwargs):
        self.source = source
        self.styles = FakeStyles()
        self.classes = ""

    @classmethod
    def get_stream(cls, widget):
        if not hasattr(widget, "_fake_stream"):
            widget._fake_stream = FakeStream(widget)
        return widget._fake_stream

    async def update(self, source):
        self.source = source


class FakeWidget:
    app = None  # set by FakeApp construction; tests always create an app

    def __init__(self, **kwargs):
        self.parent = None
        self.children = []
        self.classes = ""
        self.styles = FakeStyles()

    async def mount(self, widget):
        widget.parent = self
        self.children.append(widget)
        result = None
        if hasattr(widget, "on_mount"):
            result = widget.on_mount()
            if inspect.iscoroutine(result):
                await result
        return widget

    async def remove_children(self):
        self.children = []

    def query_one(self, selector):
        raise LookupError(selector)


class FakeVertical(FakeWidget):
    pass


class FakeVerticalScroll(FakeWidget):
    pass


class FakeTextArea(FakeWidget):
    text = ""
    required = False


class FakeLabel(FakeWidget):
    def __init__(self, text="", **kwargs):
        super().__init__()
        self.text = text


class FakeSelect(FakeWidget):
    def __init__(self, options=None, **kwargs):
        super().__init__()
        self.options = options


class FakeImage(FakeWidget):
    pass


class FakeApp:
    def __init__(self, tools=None):
        self.tool_call = types.SimpleNamespace(tools=tools or {})
        self.refresh_bindings_calls = 0
        FakeWidget.app = self

    def refresh_bindings(self):
        self.refresh_bindings_calls += 1

    def copy_to_clipboard(self, text):
        pass


def install():
    """Inject the fake modules. Call once, before importing pipeline code."""
    textual = _module("textual")
    widgets = _module("textual.widgets")
    containers = _module("textual.containers")
    message_mod = _module("textual.message")
    markdown_it = _module("markdown_it")
    textual_image = _module("textual_image")
    textual_image_widget = _module("textual_image.widget")
    cairosvg = _module("cairosvg")
    ziamath = _module("ziamath")
    pil = _module("PIL")
    pil_image = _module("PIL.Image")

    widgets.Markdown = FakeMarkdown
    widgets.TextArea = FakeTextArea
    widgets.Label = FakeLabel
    widgets.Select = FakeSelect
    containers.Vertical = FakeVertical
    containers.VerticalScroll = FakeVerticalScroll
    message_mod.Message = FakeMessage
    textual.widgets = widgets
    textual.containers = containers
    textual.message = message_mod

    class FakeMarkdownIt:
        def __init__(self, *args, **kwargs):
            pass

        def disable(self, *args, **kwargs):
            return self

    markdown_it.MarkdownIt = FakeMarkdownIt
    textual_image_widget.Image = FakeImage
    textual_image.widget = textual_image_widget
    cairosvg.svg2png = lambda *args, **kwargs: b""
    ziamath.config = types.SimpleNamespace(
        math=types.SimpleNamespace(color=None, background=None))
    ziamath.Latex = lambda *args, **kwargs: None
    pil.Image = pil_image
    pil_image.open = lambda *args, **kwargs: None
