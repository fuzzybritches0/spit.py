from textual_image.widget import Image
from spit_app.widgets import Request, RequestHeader, Response, ResponseHeader
import spit_app.latex_math as lm

mwidgets = { "request": Request, "response": Response,
            "request_header": RequestHeader, "response_header": ResponseHeader
            }

def follow_stream(app) -> None:
    if app.follow:
        app.chat_view.scroll_end(animate=False)

async def mount(app, mtype: str, content: str) -> None:
    await app.chat_view.mount(mwidgets[mtype + "_header"]())
    app.mwidget = mwidgets[mtype]()
    app.mtype = mtype
    await app.chat_view.mount(app.mwidget)
    if content:
        await app.mwidget.update(content)
    follow_stream(app)

async def mount_next(app) -> None:
    app.mwidget = mwidgets[app.mtype]()
    await app.chat_view.mount(app.mwidget)
    follow_stream(app)

async def update(app, content: str) -> None:
    await app.mwidget.update(content)
    follow_stream(app)

async def remove(app) -> None:
    await app.mwidget.remove()
    follow_stream(app)

async def mount_latex(app, latex_image: Image) -> None:
    await app.chat_view.mount(latex_image)
    follow_stream(app)

