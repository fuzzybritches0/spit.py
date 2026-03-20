import asyncio
import base64
from PIL import Image as PILImage
from io import BytesIO
from textual_image.widget import Image as TextualImage
from textual.containers import VerticalScroll

class Image(VerticalScroll):
    def __init__(self) -> None:
        super().__init__()
        self.classes = "message-content-process"
        self.finished = False

    async def finish(self, image_base64: str) -> None:
        if self.finished:
            return None
        image = image_base64
        image = image[22:]
        png = await asyncio.to_thread(base64.b64decode, image)
        pilimage = PILImage.open(BytesIO(png))
        height = round(pilimage.height / 35)
        if height < 1:
            height = 1
        image = TextualImage(pilimage, classes="image")
        image.styles.height = height
        await self.mount(image)
        self.finished = True
        self.app.applog(self.finished)
