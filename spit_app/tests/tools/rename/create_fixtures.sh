#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/../fixtures_common.sh"

fixtures_selftest || exit 1

testfile ./fixtures/t01-source.txt 'alpha\nbeta\n'
testfile ./fixtures/t01-exp-target.txt 'alpha\nbeta\n'
testfile ./fixtures/t02-source-crlf.txt 'one\r\ntwo\r\nthree\r\n'
testfile ./fixtures/t03-src-dir/inner.txt 'inside\n'
testfile ./fixtures/t03-exp-inner.txt 'inside\n'
testfile ./fixtures/t03-src-dir/deep/deeper.txt 'deepest\n'
testfile ./fixtures/t03-exp-deeper.txt 'deepest\n'
testfile ./fixtures/t04-source.txt 'dry content\n'
testfile ./fixtures/t05-a.txt 'a-content\n'
testfile ./fixtures/t05-b.txt 'b-content\n'
testfile ./fixtures/t06-source.txt 'src6\n'
testfile ./fixtures/t08-source.txt 'eight\n'
testfile ./fixtures/t09-source.txt 'nine\n'
testfile ./fixtures/t10-source.txt 'ten\n'
testfile './fixtures/t12 src file.txt' 'spaced content\n'
testfile ./fixtures/t12-exp.txt 'spaced content\n'
testfile ./fixtures/t13-a.txt 'a13\n'
testfile ./fixtures/t13-b.txt 'b13\n'
testfile ./fixtures/t14-src-dir/subdir/keep.txt 'keep\n'
testfile ./fixtures/t15-source.txt 'fifteen\n'
testfile ./fixtures/t15-target-dir/inside.txt 'inside target dir\n'
testfile_bytes ./fixtures/t17-binary.bin '\000\001\002\377'
