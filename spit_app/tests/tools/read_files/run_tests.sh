#!/bin/bash
source ../test_common.sh
trap remove_fixtures EXIT
rm -rf ./fixtures
bash ./create_fixtures.sh || exit 1
H="python3 ../harness.py"

echo "=== 1. Single file basic read ==="
out=$($H --path fixtures/lf.txt --encoding utf-8 --show_line_numbers False)
check "t1-rc" 0 $?
expect_output "t1-name" "$out" "fixtures/lf.txt"
expect_output "t1-content" "$out" "Line one"
expect_output "t1-content2" "$out" "Line three"

echo
echo "=== 2. show_line_numbers=True ==="
out=$($H --path fixtures/lf.txt --encoding utf-8 --show_line_numbers True)
check "t2-rc" 0 $?
expect_output "t2-num1" "$out" "1	Line one"
expect_output "t2-num3" "$out" "3	Line three"

echo
echo "=== 3. 2-digit padding ==="
out=$($H --path fixtures/twelve.txt --encoding utf-8 --show_line_numbers True)
check "t3-rc" 0 $?
expect_output "t3-pad1" "$out" " 1	1"
expect_output "t3-pad10" "$out" "10	10"
expect_output "t3-pad12" "$out" "12	12"

echo
echo "=== 4. CRLF file read (no raw CR in numbered output) ==="
out=$($H --path fixtures/crlf.txt --encoding utf-8 --show_line_numbers True)
check "t4-rc" 0 $?
expect_output "t4-num1" "$out" "1	Line one"
if echo "$out" | grep -qP '\r'; then
  fail=$((fail+1)); echo "FAIL: raw CR in numbered output"
else
  pass=$((pass+1))
fi

echo
echo "=== 5. Empty file ==="
out=$($H --path fixtures/empty.txt --encoding utf-8 --show_line_numbers True)
check "t5-rc" 0 $?
expect_output "t5-name" "$out" "empty.txt"

echo
echo "=== 6. No trailing newline ==="
out=$($H --path fixtures/no_trailing.txt --encoding utf-8 --show_line_numbers True)
check "t6-rc" 0 $?
expect_output "t6-num3" "$out" "3	Line three"
# Should be 3 lines, not 4
lines=$(echo "$out" | grep -cP '^\s*\d+\t')
if [ "$lines" -eq 3 ]; then
  pass=$((pass+1))
else
  fail=$((fail+1)); echo "FAIL: expected 3 numbered lines, got $lines"
fi

echo
echo "=== 7. Multi-file (JSON array path) ==="
out=$($H --path '["fixtures/lf.txt","fixtures/multi.txt"]' --encoding utf-8 --show_line_numbers False)
check "t7-rc" 0 $?
expect_output "t7-header" "$out" "Reading 2 file(s)"
expect_output "t7-sum" "$out" "2 successful"
expect_output "t7-a" "$out" "Line one"
expect_output "t7-b" "$out" "Line three"

echo
echo "=== 8. Multi-file with missing file ==="
out=$($H --path '["fixtures/lf.txt","fixtures/nope.txt"]' --encoding utf-8 --show_line_numbers False)
check "t8-rc" 0 $?
expect_output "t8-missing" "$out" "FileNotFoundError"
expect_output "t8-sum" "$out" "1 successful"

echo
echo "=== 9. Single missing file -> error ==="
out=$($H --path fixtures/nope.txt --encoding utf-8 --show_line_numbers False)
check "t9-rc" 1 $?
expect_output "t9-msg" "$out" "ERROR"

echo
echo "=== 10. Blank lines preserved ==="
out=$($H --path fixtures/blank_lines.txt --encoding utf-8 --show_line_numbers True)
check "t10-rc" 0 $?
expect_output "t10-a" "$out" "1	A"
expect_output "t10-b" "$out" "3	B"

summary
