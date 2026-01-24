import cairosvg
import ziamath
from PIL import Image as PILImage
from io import BytesIO
from textual_image.widget import Image
from textual.widgets import Markdown
from textual.containers import VerticalScroll

class LaTeX(VerticalScroll):
    BINDINGS = [
        ("y", "copy_to_clipboard", "Copy LaTeX")
    ]

    def __init__(self, latex, latex_fence_start, latex_fence_end) -> None:
        super().__init__()
        self.app.refresh_bindings()
        self.latex = latex
        escaped = ""
        if latex_fence_start == "[" or latex_fence_start == "(":
            escaped = "\\"
        self.latex_fence_start = escaped+latex_fence_start
        self.latex_fence_end = escaped+latex_fence_end
        self.watch(self.app, "theme", self.on_theme_changed, init=False)

    def action_copy_to_clipboard(self) -> None:
        self.app.copy_to_clipboard(self.latex_fence_start + self.latex + self.latex_fence_end)

    async def on_mount(self) -> None:
        self.parent.focus(scroll_visible=False)
        self.classes = "code-listing-" + self.parent.message["role"]
        color = self.styles.color.css
        background = self.styles.background.css
        latex_png = self.latex_png(self.latex, color, background)
        if latex_png:
            await self.mount(latex_png)
        else:
            self.mount(Markdown("```\n" + self.latex_fence_start + self.latex +
                                 self.latex_fence_end + "\n```"))

    def latex_png(self, latex_str: str, color: str, background: str) -> None | Image:
        ziamath.config.math.color = color
        ziamath.config.math.background = background
        try:
            expr = ziamath.Latex(latex_str)
            png = cairosvg.svg2png(expr.svg(), scale=2)
        except:
            return None
        try:
            pilimage = PILImage.open(BytesIO(png))
            image = Image(pilimage, classes="latex-image")
        except:
            return None
        height = round(pilimage.height / 35)
        if height < 1:
            height = 1
        image.styles.height = height
        return image

    async def on_theme_changed(self) -> None:
        if "latex-image" in self.children[0].classes:
            await self.remove_children()
            await self.on_mount()

