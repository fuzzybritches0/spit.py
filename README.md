# spit.py

![spit.py logo](./assets/images/logo.png)

Although this is still work in progress, it should work and keep you productive.


## What works:

- Managing multiple chats
- Managing multiple endpoints
- Managing multiple LLM settings
- Managing multiple system prompts
- Tool calling
- Using `/v1/chat/completions` endpoints
- Markdown parsing
- LaTex math formula rendering (only tested in Kitty Terminal Emulator (no ssh) and Foot Terminal Emulator (ssh too))
- Long replies (no TUI freeze, fully async)
- Chat with images
- probably more ...


## What's next:

- Agent capabilities
- GUI alternative
- Audio


# Installation instructions:


## Python venv

You might want to create a Python venv, first, to ensure no conflicts with other packages:

```
mkdir -p ~/.local/share/venv/spit.py
python3 -m venv --prompt spit.py ~/.local/share/venv/spit.py
```


## Install system dependencies

Then make sure libcairo2 is installed. We need it for LaTeX math formula rendering. On standard installations it is usually present. Try `apt list --installed | grep libcairo2` to find out! If the output of that command shows no `libcairo2`, do the following:

```
$ sudo apt install libcairo2
```


## Install and run the app

We assume you want to save the app in `~`, alias `${HOME}`. Now, install spit.py and it's dependencies:

```
$ cd ~
$ git clone https://github.com/fuzzybritches0/spit.py.git
$ source ~/.local/share/venv/spit.py/bin/activate
$ pip install textual platformdirs httpx cairosvg ziamath pillow textual_image playwright bs4 ddgs
$ playwright install chromium-headless-shell
```

We assume the Python venv is still active from the step above. You'll see `(spit.py)` at the start of your command line. If not, `source ~/.local/share/venv/spit.py/bin/activate` will do the trick. Finally, to start the app, do:

```
$ python3 ~/spit.py/main.py
```

For a more comfortable invocation you might want to save the following as a Bash script, maybe in `~/bin/spit.py`.

```bash
#!/bin/bash
source ~/.local/share/venv/spit.py/bin/activate
python3 ~/spit.py/main.py
```

Don't forget to run `chmod u+x ~/bin/spit.py` after you've saved the file. Then it will be as simple as typing `spit.py` to start the app.

The minimum settings to use the app, is to setup an endpoint. Choose 'Manage Endpoints' and then choose 'Create new endpoint' and enter the necessary settings: A name for the new endpoint and the endpoint URL is the minimum required. Then choose 'Create New Chat' to start a new chat.

If you haven't set up an endpoint, yet, head over to https://github.com/ggml-org/llama.cpp/, and find out how it's done. If you use any other provider or software with an OAI '/v1/chat/completions' compatible endpoint, I cannot guarantee that it will work, since I've only tested the llama.cpp endpoint. But it says it is compatible.


## Version requirements

Spit.py was tested with Python 3.13. It might work with other versions, too. The Textual framework version needs to be >=8.0.


## Contributions

Also, if you want to help out in developing this app, whether you are human, or AI agent, don't hesitate to open an issue, request a pull, or get in contact otherwise. My email address is on my profile page here on github.com.

Have fun and be productive.
