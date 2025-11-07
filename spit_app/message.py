from textual_image.widget import Image
from spit_app.widgets import Request, RequestHeader, Response, ResponseHeader
import spit_app.latex_math as lm

mwidgets = { "request": Request, "response": Response,
            "request_header": RequestHeader, "response_header": ResponseHeader
            }

def is_y_max(app) -> None:
    app.chat_view_y_max = False
    if app.chat_view.scroll_y + 1 >= app.chat_view.max_scroll_y:
        app.chat_view_y_max = True

def if_y_max_scroll_end(app) -> None:
    if app.chat_view_y_max:
        app.chat_view.scroll_end(animate=True)

async def mount(app, mtype: str, content: str) -> None:
    is_y_max(app)
    await app.chat_view.mount(mwidgets[mtype + "_header"]())
    app.mwidget = mwidgets[mtype]()
    app.mtype = mtype
    await app.chat_view.mount(app.mwidget)
    if content:
        await app.mwidget.update(content)
    if_y_max_scroll_end(app)

async def mount_next(app) -> None:
    is_y_max(app)
    app.mwidget = mwidgets[app.mtype]()
    await app.chat_view.mount(app.mwidget)
    if_y_max_scroll_end(app)

async def update(app, content: str) -> None:
    is_y_max(app)
    await app.mwidget.update(content)
    if_y_max_scroll_end(app)

async def remove(app) -> None:
    is_y_max(app)
    await app.mwidget.remove()
    if_y_max_scroll_end(app)

async def mount_latex(app, latex_image: Image) -> None:
    is_y_max(app)
    await app.chat_view.mount(latex_image)
    if_y_max_scroll_end(app)

async def remove_last_children(app) -> None:
    is_y_max(app)
    while len(app.chat_view.children) > app.curr_children:
        await app.chat_view.children[-1].remove()
    if_y_max_scroll_end(app)
