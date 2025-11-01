# spit.py

![spit.py logo](./assets/images/logo.png)

This is still work in progress.

What works:

- saving configurations
- using `/v1/chat/completions` endpoints
- Markdown
- LaTex math rendering (only tested in Kitty Terminal Emulator (no ssh) and Foot Terminal Emulator (ssh too))
- long replies (no TUI freeze, fully async)
- ...

What does not work:

- using llama.cpp server `/completion` endpoint (CPU optimised inference with KV caching)
- using llama.cpp python bindings as endpoint (CPU optimized inference with KV caching)
- tool calling
- saving and choosing between more than one chat
- saving and choosing between more than one system prompt
- graphical UI
- ...

# Instructions:

## Variant I:

- If you haven't already, download the latest Miniconda3 from https://repo.anaconda.com/miniconda/ and install.
- Run the following commands to set up spit.py:

```
$ sudo apt install libcairo2-dev
$ cd ~
$ git clone https://github.com/fuzzybritches0/spit.py.git
$ conda create -n spit.py python=3.13.* pip
$ conda activate spit.py
$ cd spit.py
$ pip install -r requirements.txt
```

Setup a script to run spit.py:

```bash
#!/bin/bash

~/miniconda3/bin/conda run --no-capture-output -n spit.py ~/spit.py/main.py
```

## Variant II:

If you prefer not to install with conda, you can do the following:

```
$ sudo apt install libcairo2-dev
$ cd ~
$ git clone https://github.com/fuzzybritches0/spit.py.git
$ pip install textual platformdirs httpx cairosvg ziamath pillow textual_image
```

However, if your Python version is too old, it might not work. spit.py was tested with Python >= 3.12. It might work with older versions, too.
