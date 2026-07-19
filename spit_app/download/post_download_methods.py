import tarfile
import os

class PostDownloadMethods:
    def update_llamacpp_success(app, lst: list) -> None:
        _, path = lst[0]
        try:
            tar = tarfile.open(path)
            tar.extractall(path=app.path["llamacpp"], filter="data")
            tar.close()
        except Exception as exception:
            app.exception = exception
        finally:
            try:
                os.remove(path)
            except:
                pass
