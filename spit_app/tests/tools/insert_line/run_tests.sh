#!/bin/bash
source ../test_common.sh
H="python3 ../harness.py"
# Only fixed args go in the base; line_number and dry_run are set per-test
B="--after_line None --dry_run False"

cleanup() {
  rm -f work.txt work_no_nl.txt work_empty.txt /tmp/exp9_sr.txt /tmp/exp10_sr.txt
}
trap cleanup EXIT

echo "=== 1. Insert in the middle (line_number=3) ==="
cp fixtures/original.txt work.txt
out=$($H --path work.txt --content NEW --line_number 3 ${B})
check "t1-rc" 0 $?
expect_output "t1-msg" "$out" "Inserted 1 line(s)"
expect_output "t1-where" "$out" "before line 3"
expect_file "t1-bytes" work.txt fixtures/exp_insert3.txt

echo
echo "=== 2. Insert at beginning (line_number=1) ==="
cp fixtures/original.txt work.txt
out=$($H --path work.txt --content TOP --line_number 1 ${B})
check "t2-rc" 0 $?
expect_output "t2-where" "$out" "at the beginning"
expect_file "t2-bytes" work.txt fixtures/exp_insert_top.txt

echo
echo "=== 3. Insert at end (line_number=6 = n+1) ==="
cp fixtures/original.txt work.txt
out=$($H --path work.txt --content END --line_number 6 ${B})
check "t3-rc" 0 $?
expect_output "t3-where" "$out" "at the end"
expect_file "t3-bytes" work.txt fixtures/exp_insert_end.txt

echo
echo "=== 4. after_line=5 (equivalent to end) ==="
cp fixtures/original.txt work.txt
out=$($H --path work.txt --content END --line_number 1 --after_line 5 --dry_run False)
check "t4-rc" 0 $?
expect_output "t4-where" "$out" "at the end"
expect_file "t4-bytes" work.txt fixtures/exp_insert_end.txt

echo
echo "=== 5. after_line=0 == beginning ==="
cp fixtures/original.txt work.txt
out=$($H --path work.txt --content ZERO --line_number 1 --after_line 0 --dry_run False)
check "t5-rc" 0 $?
expect_output "t5-where" "$out" "at the beginning"
head -1 work.txt | grep -qF "ZERO" && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: ZERO not first"; }

echo
echo "=== 6. Multi-line content (line_number=3) ==="
cp fixtures/original.txt work.txt
out=$($H --path work.txt --content $'A1\nA2\nA3' --line_number 3 ${B})
check "t6-rc" 0 $?
expect_output "t6-count" "$out" "Inserted 3 line(s)"
expect_file "t6-bytes" work.txt fixtures/exp_multi.txt

echo
echo "=== 7. dry_run: file unmodified ==="
cp fixtures/original.txt work.txt
md5b=$(md5 work.txt)
out=$($H --path work.txt --content GHOST --line_number 3 --after_line None --dry_run True)
check "t7-rc" 0 $?
expect_output "t7-dry" "$out" "DRY RUN"
unchanged "t7" "$md5b" "$(md5 work.txt)"

echo
echo "=== 8. Empty file → insert gets trailing newline ==="
: > work_empty.txt
out=$($H --path work_empty.txt --content FIRST --line_number 1 ${B})
check "t8-rc" 0 $?
expect_output "t8-count" "$out" "Inserted 1 line(s)"
tail -c 1 work_empty.txt | od -An -tx1 | grep -q "0a" && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: missing trailing newline"; }

echo
echo "=== 9. No trailing newline + insert at end → preserved ==="
printf 'a\nb' > work_no_nl.txt
out=$($H --path work_no_nl.txt --content NEW --line_number 3 ${B})
check "t9-rc" 0 $?
printf 'a\nb\nNEW' > /tmp/exp9_sr.txt
expect_file "t9-bytes" work_no_nl.txt /tmp/exp9_sr.txt

echo
echo "=== 10. No trailing newline + insert at beginning → preserved ==="
printf 'a\nb' > work_no_nl.txt
out=$($H --path work_no_nl.txt --content MID --line_number 1 ${B})
check "t10-rc" 0 $?
printf 'MID\na\nb' > /tmp/exp10_sr.txt
expect_file "t10-bytes" work_no_nl.txt /tmp/exp10_sr.txt

echo
echo "=== 11. Errors ==="
out=$($H --path /tmp/no_such_file_il --content X --line_number 1 ${B})
check "t11a-missing" 1 $?
expect_output "t11a-msg" "$out" "ERROR"

out=$($H --path /tmp --content X --line_number 1 ${B})
check "t11b-directory" 1 $?
expect_output "t11b-msg" "$out" "ERROR"

cp fixtures/original.txt work.txt
out=$($H --path work.txt --content X --line_number 0 ${B})
check "t11c-linenum-0" 1 $?
expect_output "t11c-msg" "$out" "out of range"

out=$($H --path work.txt --content X --line_number 7 ${B})
check "t11d-linenum-7" 1 $?
expect_output "t11d-msg" "$out" "out of range"

out=$($H --path work.txt --content X --line_number 1 --after_line 6 --dry_run False)
check "t11e-after-too-big" 1 $?
expect_output "t11e-msg" "$out" "out of range"

out=$($H --path work.txt --content X --line_number 1 --after_line -1 --dry_run False)
check "t11f-after-neg" 1 $?
expect_output "t11f-msg" "$out" "out of range"

out=$($H --path work.txt --content "" --line_number 1 ${B})
check "t11g-empty-content" 1 $?
expect_output "t11g-msg" "$out" "empty"

out=$($H --path work.txt --content X --line_number 2 --after_line 1 --dry_run False)
check "t11h-both" 1 $?
expect_output "t11h-msg" "$out" "mutually exclusive"

echo
echo "=== 12. Non-integer line_number ==="
cp fixtures/original.txt work.txt
out=$($H --path work.txt --content X --line_number abc --after_line None --dry_run False)
check "t12-non-int" 1 $?
expect_output "t12-msg" "$out" "must be an integer"

echo
echo "=== 13. String digit accepted (lenient coercion) ==="
cp fixtures/original.txt work.txt
out=$($H --path work.txt --content X --line_number 4 ${B})
check "t13-string-digit" 0 $?
sed -n '4p' work.txt | grep -qF "X" && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: X not on line 4"; }

echo
echo "=== 14. dry_run output is a valid unified diff ==="
cp fixtures/original.txt work.txt
out=$($H --path work.txt --content $'A1\nA2' --line_number 3 --after_line None --dry_run True)
check "t14-rc" 0 $?
if echo "$out" | grep -q "^---"; then pass=$((pass+1)); else fail=$((fail+1)); echo "FAIL: no --- in diff"; fi
if echo "$out" | grep -q "^+++"; then pass=$((pass+1)); else fail=$((fail+1)); echo "FAIL: no +++ in diff"; fi
if echo "$out" | grep -q "^@@"; then pass=$((pass+1)); else fail=$((fail+1)); echo "FAIL: no @@ in diff"; fi

summary
