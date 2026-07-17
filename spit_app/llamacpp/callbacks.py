import tarfile
import os

class CallbacksMixIn:
    async def update_llamacpp_failed(self, lst: list) -> None:
        failed_version = self.query_one("#llamacpp_version").value
        await self.update_input_llamacpp_version()
        self.app.action_notify(f"Failed to download {failed_version}!")

    def update_llamacpp_success(self, lst: list) -> None:
        _, path = lst[0]
        try:
            tar = tarfile.open(path)
            tar.extractall(path=self.path["llamacpp"], filter="data")
            tar.close()
            self.update_options()
        except Exception as exception:
            self.app.exception = exception
        finally:
            try:
                os.remove(path)
            except:
                pass
        self.app.action_notify(f"Download finished!")

    def download_model_success(self, lst: list) -> None:
        self.app.action_notify(f"Download finished!")

    def download_model_failed(self, lst: list) -> None:
        self.app.action_notify(f"Download failed!")
