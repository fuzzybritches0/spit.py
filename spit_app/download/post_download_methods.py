import tarfile
import shutil
import os

class PostDownloadMethods:
    def update_llamacpp_success(app, lst: list) -> None:
        _, path = lst[0]
        try:
            tar = tarfile.open(path)
            tar.extractall(path=app.path["llamacpp"], filter="data")
            tar.close()
        except Exception as exception:
            app.del_downloads_size([path])
            version = path.split("/")[-1]
            version = version.split("-")[1]
            if os.path.isdir(app.path["llamacpp"] / f"llama-{version}"):
                shutil.rmtree(app.path["llamacpp"] / f"llama-{version}")
            app.exception = exception
        finally:
            try:
                os.remove(path)
            except:
                pass
