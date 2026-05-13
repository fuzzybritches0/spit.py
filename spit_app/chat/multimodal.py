import base64
from PIL import Image, ImageOps
from io import BytesIO
import urllib.request

def image_url(base64_image) -> dict:
    return {"type": "image_url", "image_url": {"url": base64_image}}

def load_image_base64(url: str) -> str:
    if url.startswith("http://") or url.startswith("https://"):
        response = urllib.request.urlopen(url)
        image_data = response.read()
        image = Image.open(BytesIO(image_data)).convert("RGB")
    else:
        image = Image.open(url).convert("RGB")
    image = ImageOps.exif_transpose(image)
    width, height = image.size
    max_dimension = 1600
    if max(width, height) > max_dimension:
        if width > height:
            new_width = max_dimension
            new_height = int(height * (max_dimension / width))
        else:
            new_height = max_dimension
            new_width = int(width * (max_dimension / height))
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("utf-8")
