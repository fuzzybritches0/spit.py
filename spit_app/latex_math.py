# SPDX-License-Identifier: GPL-2.0
import cairosvg
import ziamath
from PIL import Image as PILImage
from io import BytesIO
from textual_image.widget import Image

def latex_math(latex_str: str) -> None | Image:
    ziamath.config.math.color = 'white'
    ziamath.config.math.background = 'black'
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

