from textual_image.widget import Image
from textual.widgets import Markdown, Static
from textual.containers import VerticalScroll
import spit_app.latex_math as lm

def is_y_max(app) -> None:
    app.chat_view_y_max = False
    if app.chat_view.scroll_y + 1 >= app.chat_view.max_scroll_y:
        app.chat_view_y_max = True

def if_y_max_scroll_end(app) -> None:
    if app.chat_view_y_max:
        app.chat_view.scroll_end(animate=False)

async def mount(app, mtype: str, content: str = "") -> None:
    is_y_max(app)
    id=len(app.chat_view.children)
    if len(app.state) > 0 and app.state[0]["role"] == "system":
        id+=1
    app.message_container = VerticalScroll(classes="message-container-"+mtype, id="id_"+str(id))
    app.mwidget = Markdown(classes=mtype)
    app.mtype = mtype
    await app.chat_view.mount(app.message_container)
    await app.message_container.mount(app.mwidget)
    app.message_container.focus()
    app.focused_message = app.message_container
    if content:
        await app.mwidget.update(content)
    if_y_max_scroll_end(app)

async def mount_next(app) -> None:
    is_y_max(app)
    app.mwidget = Markdown(classes=app.mtype)
    await app.message_container.mount(app.mwidget)
    if_y_max_scroll_end(app)

async def update(app, content: str) -> None:
    is_y_max(app)
    slen=len(app.mwidget.source)
    if app.mwidget.source == content[:slen]:
        await app.mwidget.append(content[slen:])
    else:
        await app.mwidget.update(content)
    if_y_max_scroll_end(app)

async def remove(app) -> None:
    is_y_max(app)
    await app.mwidget.remove()
    if_y_max_scroll_end(app)

async def mount_latex(app, latex_image: Image) -> None:
    is_y_max(app)
    await app.message_container.mount(latex_image)
    if_y_max_scroll_end(app)

async def remove_last_turn(app) -> None:
    if app.chat_view.children:
        is_y_max(app)
        if app.chat_view.children[-1] == app.focused_message:
            if len(app.chat_view.children) > 1:
                app.focused_message = app.chat_view.children[-2]
        await app.chat_view.children[-1].remove()
        if_y_max_scroll_end(app)
