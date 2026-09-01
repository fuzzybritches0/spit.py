#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/../fixtures_common.sh"

fixtures_selftest || exit 1

testfile ./fixtures/shared-lf.txt 'Line one\nLine two\nLine three\n'
testfile ./fixtures/t03-twelve.txt '1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12\n'
testfile ./fixtures/t04-crlf.txt 'Line one\r\nLine two\r\nLine three\r\n'
testfile ./fixtures/t05-empty.txt ''
testfile ./fixtures/t06-no-trailing.txt 'Line one\nLine two\nLine three'
testfile ./fixtures/t07-multi.txt 'Line one\nLine two\nLine three\n'
testfile ./fixtures/t10-blank-lines.txt 'A\n\nB\n\n'
