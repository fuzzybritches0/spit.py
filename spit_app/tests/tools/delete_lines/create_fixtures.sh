#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/../fixtures_common.sh"

fixtures_selftest || exit 1

testfile ./fixtures/blank_lines.txt '\n\nalpha\n\nbeta\n\n\ngamma\n'
testfile ./fixtures/empty.txt ''
testfile ./fixtures/exp_blank_pattern.txt 'alpha\nbeta\ngamma\n'
testfile ./fixtures/exp_blank_range.txt '\n\n'
testfile ./fixtures/exp_crlf_del2.txt 'one\r\nthree\r\nfour\r\n'
testfile ./fixtures/exp_crlf_del_range.txt 'one\r\nfour\r\n'
testfile ./fixtures/exp_del3.txt 'Line one\nTODO: fix this\nTODO: fix that\nLine five\n'
testfile ./fixtures/exp_del_anchored.txt 'TODO: fix this\nTODO: fix that\n'
testfile ./fixtures/exp_del_pattern.txt 'Line one\nLine three\nLine five\n'
testfile ./fixtures/exp_del_pattern_range.txt 'Line one\nLine three\nTODO: fix that\nLine five\n'
testfile ./fixtures/exp_del_range.txt 'Line one\nLine five\n'
testfile ./fixtures/exp_del_to_end.txt 'Line one\nTODO: fix this\nLine three\n'
testfile ./fixtures/exp_del_top.txt 'TODO: fix this\nLine three\nTODO: fix that\nLine five\n'
testfile ./fixtures/exp_nonl_first.txt 'b\nc'
testfile ./fixtures/exp_nonl_last.txt 'a\nb\n'
testfile ./fixtures/exp_nonl_mid.txt 'a\nc'
testfile ./fixtures/original.txt 'Line one\nTODO: fix this\nLine three\nTODO: fix that\nLine five\n'
testfile ./fixtures/original_crlf.txt 'one\r\ntwo\r\nthree\r\nfour\r\n'
testfile ./fixtures/original_no_nl.txt 'a\nb\nc'
