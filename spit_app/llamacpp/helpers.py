import os
import time
import httpx
import tarfile
import platform
from pathlib import Path

async def try_download(progress_bar, url: str, path: Path) -> bool:
    async with httpx.AsyncClient(timeout=15) as client:
        async with client.stream("GET", url, follow_redirects=True) as resp:
            if resp.status_code != 200:
                return False
            length = -1
            downloaded = 0
            if "Content-Length" in resp.headers:
                length = int(resp.headers["Content-Length"])
            if length > 0:
                progress_bar.update_total(length)
            async for binary in resp.aiter_bytes():
                progress_bar.update_progress(len(binary))
                with open(path, "ab") as f:
                    f.write(binary)
    return True

async def download_model(model: dict, path: Path) -> bool:
    org = model["org"]
    model = model["model"]
    for file in model["files"]:
        url = f"https://huggingface.co/{org}/{model}/resolve/main/{file}?download=true"
        if not await try_download(url, path / file):
            return False
    return True

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

async def download_llamacpp(progress_bar, path: Path, version: int, callback: callable) -> bool:
    machine = platform.uname().machine
    if machine == "x86_64":
        machine = "x64"
    elif machine == "aarch64":
        machine = "amd64"
    url = "https://github.com/ggml-org/llama.cpp/releases/download/"
    url += f"b{str(version)}/llama-b{str(version)}-bin-ubuntu-vulkan-{machine}.tar.gz"
    progress_bar.update_text(f"downloading version b{str(version)}...")
    tar_path = path / "llamacpp.tar.gz"
    if os.path.exists(tar_path):
        os.remove(tar_path)
    if not await try_download(progress_bar, url, tar_path):
        progress_bar.dismiss()
        return False
    tar = tarfile.open(tar_path)
    tar.extractall(path=path, filter="data")
    tar.close()
    os.remove(tar_path)
    callback()
    progress_bar.dismiss()
    return True
