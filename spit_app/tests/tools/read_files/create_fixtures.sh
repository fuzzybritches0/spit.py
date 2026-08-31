#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/../fixtures_common.sh"

fixtures_selftest || exit 1

testfile ./fixtures/blank_lines.txt 'A\n\nB\n\n'
testfile ./fixtures/crlf.txt 'Line one\r\nLine two\r\nLine three\r\n'
testfile ./fixtures/empty.txt ''
testfile ./fixtures/lf.txt 'Line one\nLine two\nLine three\n'
testfile ./fixtures/multi.txt 'Line one\nLine two\nLine three\n'
testfile ./fixtures/no_trailing.txt 'Line one\nLine two\nLine three'
testfile ./fixtures/twelve.txt '1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12\n'
