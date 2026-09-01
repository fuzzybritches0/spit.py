#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/../fixtures_common.sh"

fixtures_selftest || exit 1

testfile ./fixtures/shared-a.txt 'Line one\nLine two\nLine three\nLine four\nLine five\n'
testfile ./fixtures/shared-b.txt 'Line one\nLine two CHANGED\nLine three\nLine four\nLine five\nLine six\n'
testfile ./fixtures/t04-identical.txt 'Line one\nLine two\nLine three\nLine four\nLine five\n'
