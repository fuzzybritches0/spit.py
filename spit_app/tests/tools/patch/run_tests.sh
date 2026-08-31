#!/bin/bash
source ../test_common.sh
trap remove_fixtures EXIT
rm -rf ./fixtures
bash ./create_fixtures.sh || exit 1
FIXTURES=$PWD/fixtures
H="python3 ../harness.py"
RD_FALSE="--reverse False --dry_run False"


sed '2s/.*/Line two CHANGED/' fixtures/original.txt > fixtures/exp_changel2.txt
sed '7s/.*/Line seven CHANGED/' fixtures/original.txt > fixtures/exp_changel7.txt
sed '2s/.*/Line two CHANGED/; 9s/.*/Line nine CHANGED/' fixtures/original.txt > fixtures/exp_caret_multi.txt

echo "=== 1. Regression: standard diff (existing fixtures/patch.diff) ==="
cp fixtures/original.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --diff fixtures/patch.diff ${RD_FALSE})
check "t1-rc" 0 $?
expect_file "t1-bytes" fixtures/work.txt fixtures/expected.txt

echo
echo "=== 2. Regression: reverse ==="
cp fixtures/expected.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --diff fixtures/patch.diff --reverse True --dry_run False)
check "t2-rc" 0 $?
expect_file "t2-bytes" fixtures/work.txt fixtures/original.txt

echo
echo "=== 3. Regression: dry_run leaves file unmodified ==="
cp fixtures/original.txt fixtures/work.txt
md5b=$(md5 fixtures/work.txt)
$H --path fixtures/work.txt --diff fixtures/patch.diff --reverse False --dry_run True > /dev/null
check "t3-rc" 0 $?
unchanged "t3" "$md5b" "$(md5 fixtures/work.txt)"

echo
echo "=== 4. Wrong header counts -> error, file unchanged ==="
cp fixtures/original.txt fixtures/work.txt
md5b=$(md5 fixtures/work.txt)
out=$($H --path fixtures/work.txt --diff fixtures/wrong_count.diff ${RD_FALSE})
check "t4-rc" 1 $?
echo "$out"
unchanged "t4" "$md5b" "$(md5 fixtures/work.txt)"

echo
echo "=== 5. ^^ trailing header (relocated) ==="
cp fixtures/original.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --diff fixtures/trailing_caret.diff ${RD_FALSE})
check "t5-rc" 0 $?
expect_file "t5-bytes" fixtures/work.txt fixtures/exp_changel2.txt

echo
echo "=== 6. ^^ trailing header with wrong counts -> error ==="
cp fixtures/original.txt fixtures/work.txt
md5b=$(md5 fixtures/work.txt)
out=$($H --path fixtures/work.txt --diff fixtures/caret_wrong_count.diff ${RD_FALSE})
check "t6-rc" 1 $?
echo "$out"
unchanged "t6" "$md5b" "$(md5 fixtures/work.txt)"

echo
echo "=== 7. ^^ wins over preceding wrong @@ header ==="
cp fixtures/original.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --diff fixtures/caret_beats_at.diff ${RD_FALSE})
check "t7-rc" 0 $?
expect_file "t7-bytes" fixtures/work.txt fixtures/exp_changel2.txt

echo
echo "=== 8. Multi-hunk with ^^ trailing headers (full + abbreviated) ==="
cp fixtures/original.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --diff fixtures/caret_multi.diff ${RD_FALSE})
check "t8-rc" 0 $?
expect_file "t8-bytes" fixtures/work.txt fixtures/exp_caret_multi.txt

echo
echo "=== 9. ^^ in leading position (no body before) ==="
cp fixtures/original.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --diff fixtures/caret_leading.diff ${RD_FALSE})
check "t9-rc" 0 $?
expect_file "t9-bytes" fixtures/work.txt fixtures/exp_changel2.txt

echo
echo "=== 10. Headerless, unique body ==="
cp fixtures/original.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --diff fixtures/headerless.diff ${RD_FALSE})
check "t10-rc" 0 $?
expect_file "t10-bytes" fixtures/work.txt fixtures/exp_changel7.txt

echo
echo "=== 11. Headerless with ---/+++ file headers ==="
cp fixtures/original.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --diff fixtures/headerless_headers.diff ${RD_FALSE})
check "t11-rc" 0 $?
expect_file "t11-bytes" fixtures/work.txt fixtures/exp_changel7.txt

echo
echo "=== 12. Abbreviated header, correct counts ==="
cp fixtures/original.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --diff fixtures/abbreviated.diff ${RD_FALSE})
check "t12-rc" 0 $?
expect_file "t12-bytes" fixtures/work.txt fixtures/exp_changel2.txt

echo
echo "=== 13. Empty hunk -> error ==="
cp fixtures/original.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --diff fixtures/empty_hunk.diff ${RD_FALSE})
check "t13-rc" 1 $?
echo "$out"

echo
echo "=== 14. \\ No newline at end of file marker ==="
printf 'a\nb' > fixtures/nonl.txt
out=$($H --path fixtures/nonl.txt --diff fixtures/nonl.diff ${RD_FALSE})
check "t14-rc" 0 $?
printf 'a\nb CHANGED' > fixtures/exp_nonl.txt
expect_file "t14-bytes" fixtures/nonl.txt fixtures/exp_nonl.txt

echo
echo "=== 15. Mixed headed/headerless hunks -> error, file unchanged ==="
cp fixtures/original.txt fixtures/work.txt
md5b=$(md5 fixtures/work.txt)
out=$($H --path fixtures/work.txt --diff fixtures/mixed_headers.diff ${RD_FALSE})
check "t15-rc" 1 $?
echo "$out"
unchanged "t15" "$md5b" "$(md5 fixtures/work.txt)"

echo
echo "=== 16. Headerless ambiguous body -> error, file unchanged ==="
cp fixtures/dup.txt fixtures/work2.txt
md5b=$(md5 fixtures/work2.txt)
out=$($H --path fixtures/work2.txt --diff fixtures/ambiguous.diff ${RD_FALSE})
check "t16-rc" 1 $?
echo "$out"
unchanged "t16" "$md5b" "$(md5 fixtures/work2.txt)"

echo
echo "=== 17. Shifted header, unique match -> applied at nearest ==="
cp fixtures/original.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --diff fixtures/shifted.diff ${RD_FALSE})
check "t17-rc" 0 $?
expect_file "t17-bytes" fixtures/work.txt fixtures/exp_changel2.txt

echo
echo "=== 18. Headed, 2 candidates -> nearest to header ==="
cp fixtures/dup.txt fixtures/work2.txt
out=$($H --path fixtures/work2.txt --diff fixtures/headed_ambiguous.diff ${RD_FALSE})
check "t18-rc" 0 $?
expect_file "t18-bytes" fixtures/work2.txt fixtures/dup_headed.txt

echo
echo "=== 19. Headed, equidistant candidates -> earlier match ==="
cp fixtures/dup.txt fixtures/work2.txt
out=$($H --path fixtures/work2.txt --diff fixtures/headed_tie.diff ${RD_FALSE})
check "t19-rc" 0 $?
expect_file "t19-bytes" fixtures/work2.txt fixtures/dup_tie.txt

echo
echo "=== 20. Multi-hunk, second hunk wrong counts -> whole patch rejected ==="
cp fixtures/original.txt fixtures/work.txt
md5b=$(md5 fixtures/work.txt)
out=$($H --path fixtures/work.txt --diff fixtures/multi_wrong.diff ${RD_FALSE})
check "t20-rc" 1 $?
echo "$out"
unchanged "t20" "$md5b" "$(md5 fixtures/work.txt)"

echo
echo "=== 21. Atomic: hunk 1 applies, hunk 2 no match -> file unchanged ==="
cp fixtures/original.txt fixtures/work.txt
md5b=$(md5 fixtures/work.txt)
out=$($H --path fixtures/work.txt --diff fixtures/atomic_match.diff ${RD_FALSE})
check "t21-rc" 1 $?
echo "$out"
unchanged "t21" "$md5b" "$(md5 fixtures/work.txt)"

echo
echo "=== 22. Headerless pure insertion -> ambiguous error ==="
cp fixtures/original.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --diff fixtures/insert_only.diff ${RD_FALSE})
check "t22-rc" 1 $?
echo "$out"

echo
echo "=== 23. No hunks (only file headers) -> error ==="
cp fixtures/original.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --diff fixtures/no_hunks.diff ${RD_FALSE})
check "t23-rc" 1 $?
echo "$out"

echo
echo "=== 24. CRLF line endings preserved ==="
printf 'one\r\ntwo\r\nthree\r\n' > fixtures/crlf.txt
printf 'one\r\nTWO\r\nthree\r\n' > fixtures/crlf_exp.txt
out=$($H --path fixtures/crlf.txt --diff fixtures/crlf.diff ${RD_FALSE})
check "t24-rc" 0 $?
expect_file "t24-bytes" fixtures/crlf.txt fixtures/crlf_exp.txt

echo
echo "=== 25. CRLF reverse round-trip (byte-exact back to original) ==="
printf 'one\r\ntwo\r\nthree\r\n' > fixtures/crlf.txt
$H --path fixtures/crlf.txt --diff fixtures/crlf.diff --reverse False --dry_run False > /dev/null
$H --path fixtures/crlf.txt --diff fixtures/crlf.diff --reverse True --dry_run False > /dev/null
printf 'one\r\ntwo\r\nthree\r\n' > fixtures/crlf_back.txt
expect_file "t25-roundtrip" fixtures/crlf.txt fixtures/crlf_back.txt

echo
echo "=== 26. no-newline fixture forward+reverse round-trip (byte-exact) ==="
printf 'a\nb' > fixtures/work.txt
$H --path fixtures/work.txt --diff fixtures/nonl.diff --reverse False --dry_run False > /dev/null
$H --path fixtures/work.txt --diff fixtures/nonl.diff --reverse True --dry_run False > /dev/null
printf 'a\nb' > fixtures/exp_nonl.txt
expect_file "t26-nonl-roundtrip" fixtures/work.txt fixtures/exp_nonl.txt

echo
echo "=== 27. body line starting with '--' as first headerless line (removed, not dropped) ==="
printf -- '--x\nkeep\nmore\n' > fixtures/dashes_del.txt
out=$($H --path fixtures/dashes_del.txt --diff fixtures/del_dashes.diff ${RD_FALSE})
check "t27-rc" 0 $?
printf -- 'keep\nmore\n' > fixtures/exp_dashes_del.txt
expect_file "t27-bytes" fixtures/dashes_del.txt fixtures/exp_dashes_del.txt

echo
echo "=== 28. body line starting with '++' as first headerless line (added, not dropped) ==="
printf -- 'keep\nmore\n' > fixtures/dashes_add.txt
out=$($H --path fixtures/dashes_add.txt --diff fixtures/add_dashes.diff ${RD_FALSE})
check "t28-rc" 0 $?
printf -- '++deep\nkeep\nmore\n' > fixtures/exp_dashes_add.txt
expect_file "t28-bytes" fixtures/dashes_add.txt fixtures/exp_dashes_add.txt

echo
echo "=== 29. no-match diagnostic names the culprit line (not just line 1) ==="
cp fixtures/original.txt fixtures/culprit.txt
out=$($H --path fixtures/culprit.txt --diff fixtures/culprit.diff ${RD_FALSE})
check "t29-rc" 1 $?
expect_output "t29-culprit-line" "$out" "line 2: expected"
unchanged "t29" "$(md5 fixtures/original.txt)" "$(md5 fixtures/culprit.txt)"

summary
