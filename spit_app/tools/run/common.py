import os
import shutil
import getpass

class CommonMixIn:
    SANDBOX_ENV = "/".join(__file__.split("/")[:-1]) + "/sandbox_env.sh"

    def __init__(self, app, sandbox: bool, chat_id: str):
        self.chat_id = chat_id
        sandbox_home = app.query_one("#main").query_one(f"#{chat_id}").cs("sandbox")
        self.sandbox = sandbox
        self.sandbox_path = app.settings.path["sandbox"] / sandbox_home
        self.sandbox_path.mkdir(parents=True, exist_ok=True)
        self.sandbox_tmp = app.settings.path["sandbox_tmp"] / sandbox_home
        self.sandbox_tmp.mkdir(parents=True, exist_ok=True)
        self.sandbox_path = str(self.sandbox_path)
        self.sandbox_tmp = str(self.sandbox_tmp)
        self.user = getpass.getuser()

    def check_bwrap(self, cmd: list) -> None|str:
        if self.sandbox and not shutil.which("bwrap"):
            return "ERROR: `bwrap` not found! Give user instructions to install `bubblewrap`!"
        if not shutil.which(cmd[0]):
            return f"ERROR: `{cmd[0]}` not found!"
        return None

    def bwrap_args(self) -> list:
        nobind = ["dev", "proc", "boot", "home", "tmp"]
        args = ["bwrap"]
        for d in os.listdir("/"):
            if not d in nobind:
                args += ["--bind", f"/{d}", f"/{d}"]
        args += ["--die-with-parent"]
        args += ["--setenv", "PIP_BREAK_SYSTEM_PACKAGES", "True"]
        args += ["--setenv", "PIP_USER", "True"]
        args += ["--chdir", f"/home/{self.user}"]
        args += ["--bind", self.sandbox_path, f"/home/{self.user}"]
        args += ["--bind", self.sandbox_tmp, f"/tmp"]
        args += ["--bind", self.SANDBOX_ENV, f"/home/{self.user}/.sandbox_env.sh"]
        args += ["--unshare-all", "--share-net", "--proc", "/proc", "--dev", "/dev"]
        return args
