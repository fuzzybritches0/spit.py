#!/bin/bash
# Unit tests for the sandbox script wrapper (pure Python, no Textual needed).
cd "$(dirname $0)"
python3 ./test_trailer.py
exit $?
