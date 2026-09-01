#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/../fixtures_common.sh"

fixtures_selftest || exit 1

testfile ./fixtures/t01-src/app.py 'import os\nimport sys\n\ndef main():\n    print("hello world")\n    grep_me("once")\n    grep_me("twice")\n\nclass GrepMe:\n    def grep_me(self):\n        pass\n'
testfile ./fixtures/t01-src/blob.bin '\0000\0001\0377\0376 binary'
testfile ./fixtures/t01-src/clean.md 'no match here\n'
testfile ./fixtures/t01-src/sub/notes.txt 'line one\ngrep_me again here\nnothing on this line\nanother grep_me line\nfinal line\n'
testfile ./fixtures/t01-src/xx.txt 'foo x bar\nbaz x x qux\n'
