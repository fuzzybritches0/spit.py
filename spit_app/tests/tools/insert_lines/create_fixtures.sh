#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/../fixtures_common.sh"

fixtures_selftest || exit 1

testfile ./fixtures/shared-original.txt 'Line one\nLine two\nLine three\nLine four\nLine five\n'
testfile ./fixtures/shared-exp-insert3.txt 'Line one\nLine two\nNEW\nLine three\nLine four\nLine five\n'
testfile ./fixtures/shared-exp-insert-end.txt 'Line one\nLine two\nLine three\nLine four\nLine five\nEND\n'

testfile ./fixtures/shared-original-crlf.txt 'one\r\ntwo\r\nthree\r\n'
testfile ./fixtures/shared-original-crlf-nonl.txt 'one\r\ntwo'
testfile ./fixtures/shared-original-cr.txt 'a\rb\rc\r'
testfile ./fixtures/shared-original-mixed.txt 'a\r\nb\nc\r\n'

testfile ./fixtures/t02-exp-insert-top.txt 'TOP\nLine one\nLine two\nLine three\nLine four\nLine five\n'

testfile ./fixtures/t06-exp-multi.txt 'Line one\nLine two\nA1\nA2\nA3\nLine three\nLine four\nLine five\n'

testfile_bytes ./fixtures/t09-work-no-nl.txt 'a\nb'
testfile_bytes ./fixtures/t09-exp.txt 'a\nb\nNEW'

testfile_bytes ./fixtures/t10-work-no-nl.txt 'a\nb'
testfile_bytes ./fixtures/t10-exp.txt 'MID\na\nb'

testfile_bytes ./fixtures/t15-work-no-nl.txt 'a\nb'
testfile_bytes ./fixtures/t15-work-no-nl.txt 'a\nb'

touch ./fixtures/t16-empty.txt
testfile_bytes ./fixtures/t16-nonl.txt 'a\nb'
testfile_bytes ./fixtures/t16-blank.txt '\n\nalpha\n'

testfile_bytes ./fixtures/t17-nonl.txt 'a\nb'

testfile ./fixtures/t18-exp-crlf-mid.txt 'one\r\nMID\r\ntwo\r\nthree\r\n'
testfile ./fixtures/t18-exp-crlf-end.txt 'one\r\ntwo\r\nthree\r\nEND\r\n'
testfile ./fixtures/t18-exp-crlf-nonl-end.txt 'one\r\ntwo\r\nNEW'
testfile ./fixtures/t18-exp-cr-mid.txt 'a\rX\rb\rc\r'
testfile ./fixtures/t18-exp-mixed-mid.txt 'a\r\nX\r\nb\r\nc\r\n'
