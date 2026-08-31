#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/../fixtures_common.sh"

fixtures_selftest || exit 1

testfile ./fixtures/a.txt 'Line one\nLine two\nLine three\nLine four\nLine five\n'
testfile ./fixtures/b.txt 'Line one\nLine two CHANGED\nLine three\nLine four\nLine five\nLine six\n'
testfile ./fixtures/c.txt 'Line one\nLine two\nLine three\nLine four\nLine five\n'
