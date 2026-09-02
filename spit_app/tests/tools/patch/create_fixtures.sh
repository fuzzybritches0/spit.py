#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/../fixtures_common.sh"

fixtures_selftest || exit 1

testfile ./fixtures/corpus/original.txt 'Line one\nLine two\nLine three\nLine four\nLine five\nLine six\nLine seven\nLine eight\nLine nine\nLine ten\nLine eleven\nLine twelve\nLine thirteen\nLine fourteen\nLine fifteen\nLine sixteen\nLine seventeen\nLine eighteen\nLine nineteen\nLine twenty\n'

sed '2s/.*/Line two CHANGED/' ./fixtures/corpus/original.txt > fixtures/shared-exp-changel2.txt
sed '7s/.*/Line seven CHANGED/' ./fixtures/corpus/original.txt > fixtures/shared-exp-changel7.txt

testfile ./fixtures/corpus/expected.txt 'Line one\nLine two CHANGED\nLine three\nLine four\nLine five\nLine six\nLine eight\nLine nine\nLine ten\nLine eleven\nLine twelve\nLine thirteen\nLine fourteen\nLine fifteen\nLine inserted A\nLine inserted B\nLine sixteen\nLine seventeen\nLine eighteen\nLine nineteen\nLine twenty UPDATED\n'
testfile ./fixtures/corpus/patch.diff '--- original.txt\t2026-08-19 11:55:08.690432414 +0000\n+++ expected.txt\t2026-08-19 11:56:08.791277633 +0000\n@@ -1,10 +1,9 @@\n Line one\n-Line two\n+Line two CHANGED\n Line three\n Line four\n Line five\n Line six\n-Line seven\n Line eight\n Line nine\n Line ten\n@@ -13,8 +12,10 @@\n Line thirteen\n Line fourteen\n Line fifteen\n+Line inserted A\n+Line inserted B\n Line sixteen\n Line seventeen\n Line eighteen\n Line nineteen\n-Line twenty\n+Line twenty UPDATED\n'
testfile ./fixtures/corpus/dup.txt 'alpha\nbeta\nalpha\nbeta\nalpha\nbeta\ngamma\n'
testfile ./fixtures/corpus/dup_headed.txt 'alpha\nbeta\nalpha\nBETA\nalpha\nbeta\ngamma\n'
testfile ./fixtures/corpus/dup_tie.txt 'alpha\nBETA\nalpha\nbeta\nalpha\nbeta\ngamma\n'

testfile ./fixtures/shared-nonl.diff '@@ -1,2 +1,2 @@\n a\n-b\n\\ No newline at end of file\n+b CHANGED\n\\ No newline at end of file\n'
testfile ./fixtures/shared-crlf.diff '@@ -1,3 +1,3 @@\n one\n-two\n+TWO\n three\n'

testfile ./fixtures/t04-wrong-count.diff '--- work.txt\n+++ work.txt\n@@ -1,20 +1,21 @@\n Line one\n-Line two\n+Line two CHANGED\n Line three\n Line four\n'

testfile ./fixtures/t10-headerless.diff ' Line six\n-Line seven\n+Line seven CHANGED\n Line eight\n'

testfile ./fixtures/t11-headerless-headers.diff '--- work.txt\n+++ work.txt\n Line six\n-Line seven\n+Line seven CHANGED\n Line eight\n'

testfile ./fixtures/t12-abbreviated.diff '@@ -2 +2 @@\n-Line two\n+Line two CHANGED\n'

testfile ./fixtures/t13-empty-hunk.diff '@@ -3 +3 @@\n'

testfile_bytes ./fixtures/t14-nonl.txt 'a\nb'
testfile_bytes ./fixtures/t14-exp-nonl.txt 'a\nb CHANGED'

testfile ./fixtures/t15-mixed-headers.diff ' Line six\n-Line seven\n+Line seven CHANGED\n Line eight\n@@ -1,3 +1,3 @@\n Line one\n-Line two\n+Line two CHANGED\n Line three\n'

testfile ./fixtures/t16-ambiguous.diff ' alpha\n-beta\n+BETA\n alpha\n'

testfile ./fixtures/t17-shifted.diff '@@ -18,3 +18,3 @@\n Line one\n-Line two\n+Line two CHANGED\n Line three\n'

testfile ./fixtures/t18-headed-ambiguous.diff '@@ -3,3 +3,3 @@\n alpha\n-beta\n+BETA\n alpha\n'

testfile ./fixtures/t19-headed-tie.diff '@@ -2,3 +2,3 @@\n alpha\n-beta\n+BETA\n alpha\n'

testfile ./fixtures/t20-multi-wrong.diff '--- work.txt\n+++ work.txt\n@@ -1,10 +1,9 @@\n Line one\n-Line two\n+Line two CHANGED\n Line three\n Line four\n Line five\n Line six\n-Line seven\n Line eight\n Line nine\n Line ten\n@@ -13,15 +12,17 @@\n Line thirteen\n Line fourteen\n Line fifteen\n+Line inserted A\n+Line inserted B\n Line sixteen\n Line seventeen\n Line eighteen\n Line nineteen\n-Line twenty\n+Line twenty UPDATED\n'

testfile ./fixtures/t21-atomic-match.diff '@@ -1,3 +1,3 @@\n Line one\n-Line two\n+Line two CHANGED\n Line three\n@@ -8,3 +8,3 @@\n Line eight\n-Line NOPE\n+Line NOPE2\n Line ten\n'

testfile ./fixtures/t22-insert-only.diff '+Line inserted Z\n'

testfile ./fixtures/t23-no-hunks.diff '--- work.txt\n+++ work.txt\n'

testfile_bytes ./fixtures/t24-crlf.txt 'one\r\ntwo\r\nthree\r\n'

testfile_bytes ./fixtures/t24-crlf-exp.txt 'one\r\nTWO\r\nthree\r\n'

testfile_bytes ./fixtures/t25-crlf.txt 'one\r\ntwo\r\nthree\r\n'
testfile_bytes ./fixtures/t25-crlf-back.txt 'one\r\ntwo\r\nthree\r\n'

testfile_bytes ./fixtures/t26-work.txt 'a\nb'
testfile_bytes ./fixtures/t26-exp-nonl.txt 'a\nb'

testfile_bytes ./fixtures/t27-dashes-del.txt '--x\nkeep\nmore\n'
testfile_bytes ./fixtures/t27-exp-dashes-del.txt 'keep\nmore\n'
testfile ./fixtures/t27-del-dashes.diff '---x\n keep\n more\n'

testfile_bytes ./fixtures/t28-dashes-add.txt 'keep\nmore\n'
testfile_bytes ./fixtures/t28-exp-dashes-add.txt '++deep\nkeep\nmore\n'
testfile ./fixtures/t28-add-dashes.diff '+++deep\n keep\n more\n'

testfile ./fixtures/t29-culprit.diff '@@ -1,3 +1,3 @@\n Line one\n-Line WRONG\n+Line FIXED\n Line three\n'

testfile ./fixtures/t30-src.txt 'one\ntwo\nthree\n'
testfile ./fixtures/t30-exp.txt 'one\ntwo\ninserted\nthree\n'
testfile ./fixtures/t30-claim.diff '@@ -3 +3,2 @@\n+inserted\n'
testfile ./fixtures/t30-canonical.diff '@@ -3,0 +3,1 @@\n+inserted\n'

testfile ./fixtures/t31-all-garbage.diff '@@ -1,99 +1,99 @@\n Line one\n-Line two\n+Line two CHANGED\n Line three\n Line four\n Line five\n Line six\n-Line seven\n Line eight\n Line nine\n Line ten\n@@ -13,99 +12,99 @@\n Line thirteen\n Line fourteen\n Line fifteen\n+Line inserted A\n+Line inserted B\n Line sixteen\n Line seventeen\n Line eighteen\n Line nineteen\n-Line twenty\n+Line twenty UPDATED\n'