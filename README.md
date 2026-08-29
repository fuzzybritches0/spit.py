# spit.py

![spit.py logo](./assets/images/logo.png)

Although this is still work in progress (alpha), it should work and keep you productive.


## Supported platforms:

- Linux only


## What works:

- Managing multiple chats
- Managing multiple endpoints
- Managing models
- Managing downloaded llama.cpp versions with optional Vulkan hardware acceleration
- Managing multiple LLM settings
- Managing multiple system prompts
- Tool calling
- Multimodal (images)
- Using `/v1/chat/completions` endpoints
- Markdown parsing
- LaTex math formula rendering (only tested in Kitty Terminal Emulator (no ssh) and Foot Terminal Emulator (ssh too))
- Long replies (no TUI freeze, fully async)
- Full editing capabilities of chat history inside the chat view
- probably more ...


## What's next:

- More advanced agent capabilities
- GUI/TUI alternative to Textual
- Audio


# Installation instructions:


## Python venv

You might want to create a Python venv, first, to ensure no conflicts with other packages:

```
mkdir -p ~/.local/share/venv/spit.py
python3 -m venv --prompt spit.py ~/.local/share/venv/spit.py
```

If in the last step you got an error message about missing modules, you might have to do first:

```
$ sudo apt install python3-venv python3-pip
```


## Install system dependencies

Then make sure libcairo2, bubblewrap, and tmux are installed. We need libcairo2 for LaTeX math formula rendering and bubblewrap for sandboxing LLM function calls. We also need tmux for non-blocking background processes. On standard installations both libcairo2 and bubblewrap are usually present. With tmux it's less likely. To simply make sure they are all installed, do:

```
$ sudo apt install libcairo2 bubblewrap tmux
```


## Install and run the app

We assume you want to save the app in `~`, alias `${HOME}`. Now, install spit.py and its dependencies:

```
$ cd ~
$ git clone https://github.com/fuzzybritches0/spit.py.git
$ source ~/.local/share/venv/spit.py/bin/activate
$ pip install -r ./spit.py/requirements.txt
$ playwright install chromium-headless-shell
```

We assume the Python venv is still active from the step above. You'll see `(spit.py)` at the start of your command line. If not, `source ~/.local/share/venv/spit.py/bin/activate` will do the trick. Finally, to start the app, do:

```
$ python3 ~/spit.py/main.py
```

For a more convenient invocation you might want to save the following as a Bash script, maybe in `~/bin/spit.py`.

```bash
#!/bin/bash
source ~/.local/share/venv/spit.py/bin/activate
python3 ~/spit.py/main.py
```

Don't forget to run `chmod u+x ~/bin/spit.py` after you've saved the file. Then it will be as simple as typing `spit.py` to start the app.

To get started, click 'Manage Llamacpp' in the side-panel and scroll to the section 'Manage llama.cpp server installations' and download a llama.cpp version. The latest version should be already in the 'Llama.cpp Version' field. Then download a model of your choice in section 'Manage Models', select it as active in section 'Manage llama.cpp server settings'. Select an 'Active Version' for llama.cpp and click 'Apply'. The server should now start with a notification in the bottom right corner of your temrinal. Then click 'Create New Chat' in the side-panel and set up a new Chat.

You can also use other endpoints. Choose 'Manage Endpoints' and then choose 'Create new endpoint' and enter the necessary settings: A name for the new endpoint and the endpoint URL is the minimum required. If the endpoint requires an api-key, provide that too.

With 'Manage Endpoints', 'Manage Model Settings', and 'Server Settings', you can add or remove any custom settings to your configuration you require, provided they are understood by the endpoint or llama.cpp server.

You can find 'Server Settings' for each model you download in 'Manage Llamacpp' when you choose the model in section 'Manage Models'.

For supported server settings see: https://github.com/ggml-org/llama.cpp/tree/master/tools/server#usage

Server settings are entered without the leading `--` or `-`, e.g.: `--rope-scale` becomes `rope-scale`

For Endpoint and Model settings see: https://github.com/ggml-org/llama.cpp/tree/master/tools/server#post-completion-given-a-prompt-it-returns-the-predicted-completion


## Version requirements

Spit.py was tested with Python 3.13. It might work with other versions, too.


## Contributions

Also, if you want to help out in developing this app, whether you are human, or AI agent, don't hesitate to open an issue, request a pull, or get in contact otherwise. My email address is on my profile page here on github.com.

Have fun and be productive.
