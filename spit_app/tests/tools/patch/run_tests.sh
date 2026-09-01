#!/bin/bash
cd "$( dirname ${0})"
source ../test_common.sh
trap remove_fixtures EXIT
rm -rf ./fixtures
bash ./create_fixtures.sh || exit 1
FIXTURES=$PWD/fixtures
H="python3 ../harness.py"
RD_FALSE="--reverse False --dry_run False"

echo "=== 1. Regression: standard diff (existing fixtures/corpus/patch.diff) ==="
cp fixtures/corpus/original.txt fixtures/t01-work.txt
out=$($H --path fixtures/t01-work.txt --diff fixtures/corpus/patch.diff ${RD_FALSE})
check "t1-rc" 0 $?
expect_file "t1-bytes" fixtures/t01-work.txt fixtures/corpus/expected.txt

echo
echo "=== 2. Regression: reverse ==="
cp fixtures/corpus/expected.txt fixtures/t02-work.txt
out=$($H --path fixtures/t02-work.txt --diff fixtures/corpus/patch.diff --reverse True --dry_run False)
check "t2-rc" 0 $?
expect_file "t2-bytes" fixtures/t02-work.txt fixtures/corpus/original.txt

echo
echo "=== 3. Regression: dry_run leaves file unmodified ==="
cp fixtures/corpus/original.txt fixtures/t03-work.txt
md5b=$(md5 fixtures/t03-work.txt)
$H --path fixtures/t03-work.txt --diff fixtures/corpus/patch.diff --reverse False --dry_run True > /dev/null
check "t3-rc" 0 $?
unchanged "t3" "$md5b" "$(md5 fixtures/t03-work.txt)"

echo
echo "=== 4. Wrong header counts -> error, file unchanged ==="
cp fixtures/corpus/original.txt fixtures/t04-work.txt
md5b=$(md5 fixtures/t04-work.txt)
out=$($H --path fixtures/t04-work.txt --diff fixtures/t04-wrong-count.diff ${RD_FALSE})
check "t4-rc" 1 $?
echo "$out"
unchanged "t4" "$md5b" "$(md5 fixtures/t04-work.txt)"

echo
echo "=== 5. ^^ trailing header (relocated) ==="
cp fixtures/corpus/original.txt fixtures/t05-work.txt
out=$($H --path fixtures/t05-work.txt --diff fixtures/t05-trailing-caret.diff ${RD_FALSE})
check "t5-rc" 0 $?
expect_file "t5-bytes" fixtures/t05-work.txt fixtures/shared-exp-changel2.txt

echo
echo "=== 6. ^^ trailing header with wrong counts -> error ==="
cp fixtures/corpus/original.txt fixtures/t06-work.txt
md5b=$(md5 fixtures/t06-work.txt)
out=$($H --path fixtures/t06-work.txt --diff fixtures/t06-caret-wrong-count.diff ${RD_FALSE})
check "t6-rc" 1 $?
echo "$out"
unchanged "t6" "$md5b" "$(md5 fixtures/t06-work.txt)"

echo
echo "=== 7. ^^ wins over preceding wrong @@ header ==="
cp fixtures/corpus/original.txt fixtures/t07-work.txt
out=$($H --path fixtures/t07-work.txt --diff fixtures/t07-caret-beats-at.diff ${RD_FALSE})
check "t7-rc" 0 $?
expect_file "t7-bytes" fixtures/t07-work.txt fixtures/shared-exp-changel2.txt

echo
echo "=== 8. Multi-hunk with ^^ trailing headers (full + abbreviated) ==="
cp fixtures/corpus/original.txt fixtures/t08-work.txt
out=$($H --path fixtures/t08-work.txt --diff fixtures/t08-caret-multi.diff ${RD_FALSE})
check "t8-rc" 0 $?
expect_file "t8-bytes" fixtures/t08-work.txt fixtures/t08-exp-caret-multi.txt

echo
echo "=== 9. ^^ in leading position (no body before) ==="
cp fixtures/corpus/original.txt fixtures/t09-work.txt
out=$($H --path fixtures/t09-work.txt --diff fixtures/t09-caret-leading.diff ${RD_FALSE})
check "t9-rc" 0 $?
expect_file "t9-bytes" fixtures/t09-work.txt fixtures/shared-exp-changel2.txt

echo
echo "=== 10. Headerless, unique body ==="
cp fixtures/corpus/original.txt fixtures/t10-work.txt
out=$($H --path fixtures/t10-work.txt --diff fixtures/t10-headerless.diff ${RD_FALSE})
check "t10-rc" 0 $?
expect_file "t10-bytes" fixtures/t10-work.txt fixtures/shared-exp-changel7.txt

echo
echo "=== 11. Headerless with ---/+++ file headers ==="
cp fixtures/corpus/original.txt fixtures/t11-work.txt
out=$($H --path fixtures/t11-work.txt --diff fixtures/t11-headerless-headers.diff ${RD_FALSE})
check "t11-rc" 0 $?
expect_file "t11-bytes" fixtures/t11-work.txt fixtures/shared-exp-changel7.txt

echo
echo "=== 12. Abbreviated header, correct counts ==="
cp fixtures/corpus/original.txt fixtures/t12-work.txt
out=$($H --path fixtures/t12-work.txt --diff fixtures/t12-abbreviated.diff ${RD_FALSE})
check "t12-rc" 0 $?
expect_file "t12-bytes" fixtures/t12-work.txt fixtures/shared-exp-changel2.txt

echo
echo "=== 13. Empty hunk -> error ==="
cp fixtures/corpus/original.txt fixtures/t13-work.txt
out=$($H --path fixtures/t13-work.txt --diff fixtures/t13-empty-hunk.diff ${RD_FALSE})
check "t13-rc" 1 $?
echo "$out"

echo
echo "=== 14. \\ No newline at end of file marker ==="
out=$($H --path fixtures/t14-nonl.txt --diff fixtures/shared-nonl.diff ${RD_FALSE})
check "t14-rc" 0 $?
expect_file "t14-bytes" fixtures/t14-nonl.txt fixtures/t14-exp-nonl.txt

echo
echo "=== 15. Mixed headed/headerless hunks -> error, file unchanged ==="
cp fixtures/corpus/original.txt fixtures/t15-work.txt
md5b=$(md5 fixtures/t15-work.txt)
out=$($H --path fixtures/t15-work.txt --diff fixtures/t15-mixed-headers.diff ${RD_FALSE})
check "t15-rc" 1 $?
echo "$out"
unchanged "t15" "$md5b" "$(md5 fixtures/t15-work.txt)"

echo
echo "=== 16. Headerless ambiguous body -> error, file unchanged ==="
cp fixtures/corpus/dup.txt fixtures/t16-work2.txt
md5b=$(md5 fixtures/t16-work2.txt)
out=$($H --path fixtures/t16-work2.txt --diff fixtures/t16-ambiguous.diff ${RD_FALSE})
check "t16-rc" 1 $?
echo "$out"
unchanged "t16" "$md5b" "$(md5 fixtures/t16-work2.txt)"

echo
echo "=== 17. Shifted header, unique match -> applied at nearest ==="
cp fixtures/corpus/original.txt fixtures/t17-work.txt
out=$($H --path fixtures/t17-work.txt --diff fixtures/t17-shifted.diff ${RD_FALSE})
check "t17-rc" 0 $?
expect_file "t17-bytes" fixtures/t17-work.txt fixtures/shared-exp-changel2.txt

echo
echo "=== 18. Headed, 2 candidates -> nearest to header ==="
cp fixtures/corpus/dup.txt fixtures/t18-work2.txt
out=$($H --path fixtures/t18-work2.txt --diff fixtures/t18-headed-ambiguous.diff ${RD_FALSE})
check "t18-rc" 0 $?
expect_file "t18-bytes" fixtures/t18-work2.txt fixtures/corpus/dup_headed.txt

echo
echo "=== 19. Headed, equidistant candidates -> earlier match ==="
cp fixtures/corpus/dup.txt fixtures/t19-work2.txt
out=$($H --path fixtures/t19-work2.txt --diff fixtures/t19-headed-tie.diff ${RD_FALSE})
check "t19-rc" 0 $?
expect_file "t19-bytes" fixtures/t19-work2.txt fixtures/corpus/dup_tie.txt

echo
echo "=== 20. Multi-hunk, second hunk wrong counts -> whole patch rejected ==="
cp fixtures/corpus/original.txt fixtures/t20-work.txt
md5b=$(md5 fixtures/t20-work.txt)
out=$($H --path fixtures/t20-work.txt --diff fixtures/t20-multi-wrong.diff ${RD_FALSE})
check "t20-rc" 1 $?
echo "$out"
unchanged "t20" "$md5b" "$(md5 fixtures/t20-work.txt)"

echo
echo "=== 21. Atomic: hunk 1 applies, hunk 2 no match -> file unchanged ==="
cp fixtures/corpus/original.txt fixtures/t21-work.txt
md5b=$(md5 fixtures/t21-work.txt)
out=$($H --path fixtures/t21-work.txt --diff fixtures/t21-atomic-match.diff ${RD_FALSE})
check "t21-rc" 1 $?
echo "$out"
unchanged "t21" "$md5b" "$(md5 fixtures/t21-work.txt)"

echo
echo "=== 22. Headerless pure insertion -> ambiguous error ==="
cp fixtures/corpus/original.txt fixtures/t22-work.txt
out=$($H --path fixtures/t22-work.txt --diff fixtures/t22-insert-only.diff ${RD_FALSE})
check "t22-rc" 1 $?
echo "$out"

echo
echo "=== 23. No hunks (only file headers) -> error ==="
cp fixtures/corpus/original.txt fixtures/t23-work.txt
out=$($H --path fixtures/t23-work.txt --diff fixtures/t23-no-hunks.diff ${RD_FALSE})
check "t23-rc" 1 $?
echo "$out"

echo
echo "=== 24. CRLF line endings preserved ==="
out=$($H --path fixtures/t24-crlf.txt --diff fixtures/shared-crlf.diff ${RD_FALSE})
check "t24-rc" 0 $?
expect_file "t24-bytes" fixtures/t24-crlf.txt fixtures/t24-crlf-exp.txt

echo
echo "=== 25. CRLF reverse round-trip (byte-exact back to original) ==="
$H --path fixtures/t25-crlf.txt --diff fixtures/shared-crlf.diff --reverse False --dry_run False > /dev/null
$H --path fixtures/t25-crlf.txt --diff fixtures/shared-crlf.diff --reverse True --dry_run False > /dev/null
expect_file "t25-roundtrip" fixtures/t25-crlf.txt fixtures/t25-crlf-back.txt

echo
echo "=== 26. no-newline fixture forward+reverse round-trip (byte-exact) ==="
$H --path fixtures/t26-work.txt --diff fixtures/shared-nonl.diff --reverse False --dry_run False > /dev/null
$H --path fixtures/t26-work.txt --diff fixtures/shared-nonl.diff --reverse True --dry_run False > /dev/null
expect_file "t26-nonl-roundtrip" fixtures/t26-work.txt fixtures/t26-exp-nonl.txt

echo
echo "=== 27. body line starting with '--' as first headerless line (removed, not dropped) ==="
out=$($H --path fixtures/t27-dashes-del.txt --diff fixtures/t27-del-dashes.diff ${RD_FALSE})
check "t27-rc" 0 $?
expect_file "t27-bytes" fixtures/t27-dashes-del.txt fixtures/t27-exp-dashes-del.txt

echo
echo "=== 28. body line starting with '++' as first headerless line (added, not dropped) ==="
out=$($H --path fixtures/t28-dashes-add.txt --diff fixtures/t28-add-dashes.diff ${RD_FALSE})
check "t28-rc" 0 $?
expect_file "t28-bytes" fixtures/t28-dashes-add.txt fixtures/t28-exp-dashes-add.txt

echo
echo "=== 29. no-match diagnostic names the culprit line (not just line 1) ==="
cp fixtures/corpus/original.txt fixtures/t29-culprit.txt
out=$($H --path fixtures/t29-culprit.txt --diff fixtures/t29-culprit.diff ${RD_FALSE})
check "t29-rc" 1 $?
expect_output "t29-culprit-line" "$out" "line 2: expected"
unchanged "t29" "$(md5 fixtures/corpus/original.txt)" "$(md5 fixtures/t29-culprit.txt)"

summary
