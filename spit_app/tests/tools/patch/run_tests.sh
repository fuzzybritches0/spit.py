#!/bin/bash
source ../test_common.sh
H="python3 ../harness.py"
RD_FALSE="--reverse False --dry_run False"

cleanup() {
  rm -f work.txt work2.txt nonl.txt exp_nonl.txt
  rm -f exp_changel2.txt exp_changel7.txt exp_caret_multi.txt
  rm -f crlf.txt crlf_exp.txt crlf_back.txt dashes_del.txt dashes_add.txt culprit.txt
  rm -f exp_dashes_del.txt exp_dashes_add.txt
}
trap cleanup EXIT

sed '2s/.*/Line two CHANGED/' original.txt > exp_changel2.txt
sed '7s/.*/Line seven CHANGED/' original.txt > exp_changel7.txt
sed '2s/.*/Line two CHANGED/; 9s/.*/Line nine CHANGED/' original.txt > exp_caret_multi.txt

echo "=== 1. Regression: standard diff (existing patch.diff) ==="
cp original.txt work.txt
out=$($H --path work.txt --diff patch.diff ${RD_FALSE})
check "t1-rc" 0 $?
expect_file "t1-bytes" work.txt expected.txt

echo
echo "=== 2. Regression: reverse ==="
cp expected.txt work.txt
out=$($H --path work.txt --diff patch.diff --reverse True --dry_run False)
check "t2-rc" 0 $?
expect_file "t2-bytes" work.txt original.txt

echo
echo "=== 3. Regression: dry_run leaves file unmodified ==="
cp original.txt work.txt
md5b=$(md5 work.txt)
$H --path work.txt --diff patch.diff --reverse False --dry_run True > /dev/null
check "t3-rc" 0 $?
unchanged "t3" "$md5b" "$(md5 work.txt)"

echo
echo "=== 4. Wrong header counts -> error, file unchanged ==="
cp original.txt work.txt
md5b=$(md5 work.txt)
out=$($H --path work.txt --diff fixtures/wrong_count.diff ${RD_FALSE})
check "t4-rc" 1 $?
echo "$out"
unchanged "t4" "$md5b" "$(md5 work.txt)"

echo
echo "=== 5. ^^ trailing header (relocated) ==="
cp original.txt work.txt
out=$($H --path work.txt --diff fixtures/trailing_caret.diff ${RD_FALSE})
check "t5-rc" 0 $?
expect_file "t5-bytes" work.txt exp_changel2.txt

echo
echo "=== 6. ^^ trailing header with wrong counts -> error ==="
cp original.txt work.txt
md5b=$(md5 work.txt)
out=$($H --path work.txt --diff fixtures/caret_wrong_count.diff ${RD_FALSE})
check "t6-rc" 1 $?
echo "$out"
unchanged "t6" "$md5b" "$(md5 work.txt)"

echo
echo "=== 7. ^^ wins over preceding wrong @@ header ==="
cp original.txt work.txt
out=$($H --path work.txt --diff fixtures/caret_beats_at.diff ${RD_FALSE})
check "t7-rc" 0 $?
expect_file "t7-bytes" work.txt exp_changel2.txt

echo
echo "=== 8. Multi-hunk with ^^ trailing headers (full + abbreviated) ==="
cp original.txt work.txt
out=$($H --path work.txt --diff fixtures/caret_multi.diff ${RD_FALSE})
check "t8-rc" 0 $?
expect_file "t8-bytes" work.txt exp_caret_multi.txt

echo
echo "=== 9. ^^ in leading position (no body before) ==="
cp original.txt work.txt
out=$($H --path work.txt --diff fixtures/caret_leading.diff ${RD_FALSE})
check "t9-rc" 0 $?
expect_file "t9-bytes" work.txt exp_changel2.txt

echo
echo "=== 10. Headerless, unique body ==="
cp original.txt work.txt
out=$($H --path work.txt --diff fixtures/headerless.diff ${RD_FALSE})
check "t10-rc" 0 $?
expect_file "t10-bytes" work.txt exp_changel7.txt

echo
echo "=== 11. Headerless with ---/+++ file headers ==="
cp original.txt work.txt
out=$($H --path work.txt --diff fixtures/headerless_headers.diff ${RD_FALSE})
check "t11-rc" 0 $?
expect_file "t11-bytes" work.txt exp_changel7.txt

echo
echo "=== 12. Abbreviated header, correct counts ==="
cp original.txt work.txt
out=$($H --path work.txt --diff fixtures/abbreviated.diff ${RD_FALSE})
check "t12-rc" 0 $?
expect_file "t12-bytes" work.txt exp_changel2.txt

echo
echo "=== 13. Empty hunk -> error ==="
cp original.txt work.txt
out=$($H --path work.txt --diff fixtures/empty_hunk.diff ${RD_FALSE})
check "t13-rc" 1 $?
echo "$out"

echo
echo "=== 14. \\ No newline at end of file marker ==="
printf 'a\nb' > nonl.txt
out=$($H --path nonl.txt --diff fixtures/nonl.diff ${RD_FALSE})
check "t14-rc" 0 $?
printf 'a\nb CHANGED' > exp_nonl.txt
expect_file "t14-bytes" nonl.txt exp_nonl.txt

echo
echo "=== 15. Mixed headed/headerless hunks -> error, file unchanged ==="
cp original.txt work.txt
md5b=$(md5 work.txt)
out=$($H --path work.txt --diff fixtures/mixed_headers.diff ${RD_FALSE})
check "t15-rc" 1 $?
echo "$out"
unchanged "t15" "$md5b" "$(md5 work.txt)"

echo
echo "=== 16. Headerless ambiguous body -> error, file unchanged ==="
cp dup.txt work2.txt
md5b=$(md5 work2.txt)
out=$($H --path work2.txt --diff fixtures/ambiguous.diff ${RD_FALSE})
check "t16-rc" 1 $?
echo "$out"
unchanged "t16" "$md5b" "$(md5 work2.txt)"

echo
echo "=== 17. Shifted header, unique match -> applied at nearest ==="
cp original.txt work.txt
out=$($H --path work.txt --diff fixtures/shifted.diff ${RD_FALSE})
check "t17-rc" 0 $?
expect_file "t17-bytes" work.txt exp_changel2.txt

echo
echo "=== 18. Headed, 2 candidates -> nearest to header ==="
cp dup.txt work2.txt
out=$($H --path work2.txt --diff fixtures/headed_ambiguous.diff ${RD_FALSE})
check "t18-rc" 0 $?
expect_file "t18-bytes" work2.txt dup_headed.txt

echo
echo "=== 19. Headed, equidistant candidates -> earlier match ==="
cp dup.txt work2.txt
out=$($H --path work2.txt --diff fixtures/headed_tie.diff ${RD_FALSE})
check "t19-rc" 0 $?
expect_file "t19-bytes" work2.txt dup_tie.txt

echo
echo "=== 20. Multi-hunk, second hunk wrong counts -> whole patch rejected ==="
cp original.txt work.txt
md5b=$(md5 work.txt)
out=$($H --path work.txt --diff fixtures/multi_wrong.diff ${RD_FALSE})
check "t20-rc" 1 $?
echo "$out"
unchanged "t20" "$md5b" "$(md5 work.txt)"

echo
echo "=== 21. Atomic: hunk 1 applies, hunk 2 no match -> file unchanged ==="
cp original.txt work.txt
md5b=$(md5 work.txt)
out=$($H --path work.txt --diff fixtures/atomic_match.diff ${RD_FALSE})
check "t21-rc" 1 $?
echo "$out"
unchanged "t21" "$md5b" "$(md5 work.txt)"

echo
echo "=== 22. Headerless pure insertion -> ambiguous error ==="
cp original.txt work.txt
out=$($H --path work.txt --diff fixtures/insert_only.diff ${RD_FALSE})
check "t22-rc" 1 $?
echo "$out"

echo
echo "=== 23. No hunks (only file headers) -> error ==="
cp original.txt work.txt
out=$($H --path work.txt --diff fixtures/no_hunks.diff ${RD_FALSE})
check "t23-rc" 1 $?
echo "$out"

echo
echo "=== 24. CRLF line endings preserved ==="
printf 'one\r\ntwo\r\nthree\r\n' > crlf.txt
printf 'one\r\nTWO\r\nthree\r\n' > crlf_exp.txt
out=$($H --path crlf.txt --diff fixtures/crlf.diff ${RD_FALSE})
check "t24-rc" 0 $?
expect_file "t24-bytes" crlf.txt crlf_exp.txt

echo
echo "=== 25. CRLF reverse round-trip (byte-exact back to original) ==="
printf 'one\r\ntwo\r\nthree\r\n' > crlf.txt
$H --path crlf.txt --diff fixtures/crlf.diff --reverse False --dry_run False > /dev/null
$H --path crlf.txt --diff fixtures/crlf.diff --reverse True --dry_run False > /dev/null
printf 'one\r\ntwo\r\nthree\r\n' > crlf_back.txt
expect_file "t25-roundtrip" crlf.txt crlf_back.txt

echo
echo "=== 26. no-newline fixture forward+reverse round-trip (byte-exact) ==="
printf 'a\nb' > work.txt
$H --path work.txt --diff fixtures/nonl.diff --reverse False --dry_run False > /dev/null
$H --path work.txt --diff fixtures/nonl.diff --reverse True --dry_run False > /dev/null
printf 'a\nb' > exp_nonl.txt
expect_file "t26-nonl-roundtrip" work.txt exp_nonl.txt

echo
echo "=== 27. body line starting with '--' as first headerless line (removed, not dropped) ==="
printf -- '--x\nkeep\nmore\n' > dashes_del.txt
out=$($H --path dashes_del.txt --diff fixtures/del_dashes.diff ${RD_FALSE})
check "t27-rc" 0 $?
printf -- 'keep\nmore\n' > exp_dashes_del.txt
expect_file "t27-bytes" dashes_del.txt exp_dashes_del.txt

echo
echo "=== 28. body line starting with '++' as first headerless line (added, not dropped) ==="
printf -- 'keep\nmore\n' > dashes_add.txt
out=$($H --path dashes_add.txt --diff fixtures/add_dashes.diff ${RD_FALSE})
check "t28-rc" 0 $?
printf -- '++deep\nkeep\nmore\n' > exp_dashes_add.txt
expect_file "t28-bytes" dashes_add.txt exp_dashes_add.txt

echo
echo "=== 29. no-match diagnostic names the culprit line (not just line 1) ==="
cp original.txt culprit.txt
out=$($H --path culprit.txt --diff fixtures/culprit.diff ${RD_FALSE})
check "t29-rc" 1 $?
expect_output "t29-culprit-line" "$out" "line 2: expected"
unchanged "t29" "$(md5 original.txt)" "$(md5 culprit.txt)"

summary
