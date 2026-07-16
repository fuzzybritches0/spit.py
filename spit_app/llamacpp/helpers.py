import time
import httpx
import asyncio
from pathlib import Path

async def get_vulkan_devices(llama_server: Path) -> list:
    llama_server = llama_server / "llama-server"
    devices = []
    try:
        output = await run_get_output([str(llama_server), "--list-devices"])
        for line in output.split("\n"):
            if line.strip().startswith("Vulkan"):
                devices.append(line.strip().split(":")[0].strip())
        return devices
    except:
        return []

async def run_get_output(cmd: list) -> str:
    output = ""
    async for line in run(cmd):
        output += line
    return output

async def run(cmd: list):
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE,
                                                stderr=asyncio.subprocess.STDOUT,
                                                start_new_session=True)
    stdout, _ = await proc.communicate()
    for line in stdout.decode("UTF-8", errors="replace").splitlines(keepends=True):
        yield line

async def get_latest_llamacpp_version(settings) -> int:
    if "latest" in settings.llamacpp and "latest_time" in settings.llamacpp:
        if time.time() < settings.llamacpp["latest_time"] + 3600:
            return settings.llamacpp["latest"]
    url = "https://github.com/ggml-org/llama.cpp/releases/latest"
    async with httpx.AsyncClient(timeout=15) as client:
        async with client.stream("GET", url, follow_redirects=True) as resp:
            if resp.status_code != 200:
                return -1
            async for line in resp.aiter_lines():
                if "<title>" in line:
                    line = line.strip()
                    try:
                        version = int(line.split(" ")[1][1:])
                    except:
                        version = 0
                    finally:
                        if not version == 0:
                            settings.llamacpp["latest"] = version
                            settings.llamacpp["latest_time"] = time.time()
                            settings.save()
                        return version
    return -2
