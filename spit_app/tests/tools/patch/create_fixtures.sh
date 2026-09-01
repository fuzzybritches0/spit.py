#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/../fixtures_common.sh"

fixtures_selftest || exit 1

testfile ./fixtures/corpus/original.txt 'Line one\nLine two\nLine three\nLine four\nLine five\nLine six\nLine seven\nLine eight\nLine nine\nLine ten\nLine eleven\nLine twelve\nLine thirteen\nLine fourteen\nLine fifteen\nLine sixteen\nLine seventeen\nLine eighteen\nLine nineteen\nLine twenty\n'
testfile ./fixtures/corpus/expected.txt 'Line one\nLine two CHANGED\nLine three\nLine four\nLine five\nLine six\nLine eight\nLine nine\nLine ten\nLine eleven\nLine twelve\nLine thirteen\nLine fourteen\nLine fifteen\nLine inserted A\nLine inserted B\nLine sixteen\nLine seventeen\nLine eighteen\nLine nineteen\nLine twenty UPDATED\n'
testfile ./fixtures/corpus/patch.diff '--- original.txt\t2026-08-19 11:55:08.690432414 +0000\n+++ expected.txt\t2026-08-19 11:56:08.791277633 +0000\n@@ -1,10 +1,9 @@\n Line one\n-Line two\n+Line two CHANGED\n Line three\n Line four\n Line five\n Line six\n-Line seven\n Line eight\n Line nine\n Line ten\n@@ -13,8 +12,10 @@\n Line thirteen\n Line fourteen\n Line fifteen\n+Line inserted A\n+Line inserted B\n Line sixteen\n Line seventeen\n Line eighteen\n Line nineteen\n-Line twenty\n+Line twenty UPDATED\n'
testfile ./fixtures/corpus/dup.txt 'alpha\nbeta\nalpha\nbeta\nalpha\nbeta\ngamma\n'
testfile ./fixtures/corpus/dup_headed.txt 'alpha\nbeta\nalpha\nBETA\nalpha\nbeta\ngamma\n'
testfile ./fixtures/corpus/dup_tie.txt 'alpha\nBETA\nalpha\nbeta\nalpha\nbeta\ngamma\n'

testfile ./fixtures/shared-nonl.diff '@@ -1,2 +1,2 @@\n a\n-b\n\\ No newline at end of file\n+b CHANGED\n\\ No newline at end of file\n'
testfile ./fixtures/shared-crlf.diff '@@ -1,3 +1,3 @@\n one\n-two\n+TWO\n three\n'

testfile ./fixtures/t04-wrong-count.diff '--- work.txt\n+++ work.txt\n@@ -1,20 +1,21 @@\n Line one\n-Line two\n+Line two CHANGED\n Line three\n Line four\n'
testfile ./fixtures/t05-trailing-caret.diff ' Line one\n-Line two\n+Line two CHANGED\n Line three\n Line four\n^^ -1,4 +1,4 ^^\n'
testfile ./fixtures/t06-caret-wrong-count.diff ' Line one\n-Line two\n+Line two CHANGED\n Line three\n Line four\n^^ -1,9 +1,9 ^^\n'
testfile ./fixtures/t07-caret-beats-at.diff '@@ -1,10 +1,11 @@\n Line one\n-Line two\n+Line two CHANGED\n Line three\n^^ -1,3 +1,3 ^^\n'
testfile ./fixtures/t08-caret-multi.diff ' Line one\n-Line two\n+Line two CHANGED\n Line three\n^^ -1,3 +1,3 ^^\n-Line nine\n+Line nine CHANGED\n^^ -9 +9 ^^\n'
testfile ./fixtures/t09-caret-leading.diff '^^ -1,3 +1,3 ^^\n Line one\n-Line two\n+Line two CHANGED\n Line three\n'
testfile ./fixtures/t10-headerless.diff ' Line six\n-Line seven\n+Line seven CHANGED\n Line eight\n'
testfile ./fixtures/t11-headerless-headers.diff '--- work.txt\n+++ work.txt\n Line six\n-Line seven\n+Line seven CHANGED\n Line eight\n'
testfile ./fixtures/t12-abbreviated.diff '@@ -2 +2 @@\n-Line two\n+Line two CHANGED\n'
testfile ./fixtures/t13-empty-hunk.diff '@@ -3 +3 @@\n'
testfile ./fixtures/t15-mixed-headers.diff ' Line six\n-Line seven\n+Line seven CHANGED\n Line eight\n@@ -1,3 +1,3 @@\n Line one\n-Line two\n+Line two CHANGED\n Line three\n'
testfile ./fixtures/t16-ambiguous.diff ' alpha\n-beta\n+BETA\n alpha\n'
testfile ./fixtures/t17-shifted.diff '@@ -18,3 +18,3 @@\n Line one\n-Line two\n+Line two CHANGED\n Line three\n'
testfile ./fixtures/t18-headed-ambiguous.diff '@@ -3,3 +3,3 @@\n alpha\n-beta\n+BETA\n alpha\n'
testfile ./fixtures/t19-headed-tie.diff '@@ -2,3 +2,3 @@\n alpha\n-beta\n+BETA\n alpha\n'
testfile ./fixtures/t20-multi-wrong.diff '--- work.txt\n+++ work.txt\n@@ -1,10 +1,9 @@\n Line one\n-Line two\n+Line two CHANGED\n Line three\n Line four\n Line five\n Line six\n-Line seven\n Line eight\n Line nine\n Line ten\n@@ -13,15 +12,17 @@\n Line thirteen\n Line fourteen\n Line fifteen\n+Line inserted A\n+Line inserted B\n Line sixteen\n Line seventeen\n Line eighteen\n Line nineteen\n-Line twenty\n+Line twenty UPDATED\n'
testfile ./fixtures/t21-atomic-match.diff '@@ -1,3 +1,3 @@\n Line one\n-Line two\n+Line two CHANGED\n Line three\n@@ -8,3 +8,3 @@\n Line eight\n-Line NOPE\n+Line NOPE2\n Line ten\n'
testfile ./fixtures/t22-insert-only.diff '+Line inserted Z\n'
testfile ./fixtures/t23-no-hunks.diff '--- work.txt\n+++ work.txt\n'
testfile ./fixtures/t27-del-dashes.diff '---x\n keep\n more\n'
testfile ./fixtures/t28-add-dashes.diff '+++deep\n keep\n more\n'
testfile ./fixtures/t29-culprit.diff '@@ -1,3 +1,3 @@\n Line one\n-Line WRONG\n+Line FIXED\n Line three\n'
