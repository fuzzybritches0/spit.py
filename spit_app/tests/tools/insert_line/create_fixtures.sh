#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/../fixtures_common.sh"

fixtures_selftest || exit 1

testfile ./fixtures/exp_cr_mid.txt 'a\rX\rb\rc\r'
testfile ./fixtures/exp_crlf_end.txt 'one\r\ntwo\r\nthree\r\nEND\r\n'
testfile ./fixtures/exp_crlf_mid.txt 'one\r\nMID\r\ntwo\r\nthree\r\n'
testfile ./fixtures/exp_crlf_nonl_end.txt 'one\r\ntwo\r\nNEW'
testfile ./fixtures/exp_insert3.txt 'Line one\nLine two\nNEW\nLine three\nLine four\nLine five\n'
testfile ./fixtures/exp_insert_end.txt 'Line one\nLine two\nLine three\nLine four\nLine five\nEND\n'
testfile ./fixtures/exp_insert_top.txt 'TOP\nLine one\nLine two\nLine three\nLine four\nLine five\n'
testfile ./fixtures/exp_mixed_mid.txt 'a\r\nX\r\nb\r\nc\r\n'
testfile ./fixtures/exp_multi.txt 'Line one\nLine two\nA1\nA2\nA3\nLine three\nLine four\nLine five\n'
testfile ./fixtures/original.txt 'Line one\nLine two\nLine three\nLine four\nLine five\n'
testfile ./fixtures/original_cr.txt 'a\rb\rc\r'
testfile ./fixtures/original_crlf.txt 'one\r\ntwo\r\nthree\r\n'
testfile ./fixtures/original_crlf_nonl.txt 'one\r\ntwo'
testfile ./fixtures/original_mixed.txt 'a\r\nb\nc\r\n'
