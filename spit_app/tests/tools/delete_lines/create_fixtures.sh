#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/../fixtures_common.sh"

fixtures_selftest || exit 1

testfile ./fixtures/shared-original.txt 'Line one\nTODO: fix this\nLine three\nTODO: fix that\nLine five\n'
testfile ./fixtures/shared-exp-del3.txt 'Line one\nTODO: fix this\nTODO: fix that\nLine five\n'
testfile ./fixtures/t03-exp-del-range.txt 'Line one\nLine five\n'
testfile ./fixtures/t04-exp-del-to-end.txt 'Line one\nTODO: fix this\nLine three\n'
testfile ./fixtures/t05-exp-del-top.txt 'TODO: fix this\nLine three\nTODO: fix that\nLine five\n'
testfile ./fixtures/t06-exp-del-pattern.txt 'Line one\nLine three\nLine five\n'
testfile ./fixtures/t07-exp-del-pattern-range.txt 'Line one\nLine three\nTODO: fix that\nLine five\n'
testfile ./fixtures/t08-exp-del-anchored.txt 'TODO: fix this\nTODO: fix that\n'
testfile ./fixtures/t17-exp-nonl-mid.txt 'a\nc'
testfile ./fixtures/t17-exp-nonl-last.txt 'a\nb\n'
testfile ./fixtures/t17-exp-nonl-first.txt 'b\nc'
testfile ./fixtures/shared-original-no-nl.txt 'a\nb\nc'
testfile ./fixtures/t18-exp-crlf-del2.txt 'one\r\nthree\r\nfour\r\n'
testfile ./fixtures/t18-exp-crlf-del-range.txt 'one\r\nfour\r\n'
testfile ./fixtures/shared-original-crlf.txt 'one\r\ntwo\r\nthree\r\nfour\r\n'
testfile ./fixtures/t21-exp-blank-pattern.txt 'alpha\nbeta\ngamma\n'
testfile ./fixtures/t21-exp-blank-range.txt '\n\n'
testfile ./fixtures/shared-blank-lines.txt '\n\nalpha\n\nbeta\n\n\ngamma\n'
