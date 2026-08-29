import os
import sys
import types
import json
from pathlib import Path
import subprocess

def py(value):
    if value.lower() == "false":
        return False
    if value.lower() == "true":
        return True
    if value.lower() == "none" or value.lower() == "null":
        return None
    try:
        return int(value)
    except ValueError:
        pass
    if value.startswith("[") or value.startswith("{"):
        try:
            json.loads(value)
            return value
        except json.JSONDecodeError:
            pass
    return json.dumps(value)

class Harness:
    def __init__(self, script: str, args: list) -> None:
        self.script = script
        self.args = args

    def _run(self, head: str) -> int:
        r = subprocess.run([sys.executable], input=head+self.script, capture_output=True, text=True)
        if r.stdout:
            print(r.stdout, end="")
        if r.stderr:
            print("STDERR:", r.stderr, file=sys.stderr)
        return r.returncode

    def run(self) -> None:
        head = ""
        for arg in self.args:
            if f"--{arg}" in sys.argv:
                value = py(sys.argv[sys.argv.index(f"--{arg}") + 1])
                head += f"{arg} = {value}\n"
        sys.exit(self._run(head))

setup = Path.cwd() / "setup.json"
if os.path.isfile(setup):
    setup = json.loads(setup.read_text())
    script = open(setup["script"]).read()
    harness = Harness(script, setup["args"])
    harness.run()
