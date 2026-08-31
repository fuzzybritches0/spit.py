#!/bin/bash
source ../test_common.sh
trap remove_fixtures EXIT
rm -rf ./fixtures
bash ./create_fixtures.sh || exit 1
H="python3 ../harness.py"


echo "=== 1. Basic grep: match pattern in directory ==="
out=$($H --path fixtures/src --pattern grep_me --file_pattern "*" --recursive True --context 0 --max_results 100)
check "t1-rc" 0 $?
expect_output "t1-count" "$out" "Found 5 match(es)"
expect_output "t1-app" "$out" "app.py:6:"
expect_output "t1-notes" "$out" "notes.txt:2:"

echo
echo "=== 2. File pattern filter ==="
out=$($H --path fixtures/src --pattern grep_me --file_pattern "*.py" --recursive True --context 0 --max_results 100)
check "t2-rc" 0 $?
expect_output "t2-count" "$out" "Found 3 match(es)"
if echo "$out" | grep -q "notes.txt"; then
  fail=$((fail+1)); echo "FAIL: should not match .txt"
else
  pass=$((pass+1))
fi

echo
echo "=== 3. Non-recursive ==="
out=$($H --path fixtures/src --pattern grep_me --file_pattern "*" --recursive False --context 0 --max_results 100)
check "t3-rc" 0 $?
expect_output "t3-count" "$out" "Found 3 match(es)"
if echo "$out" | grep -q "notes.txt"; then
  fail=$((fail+1)); echo "FAIL: sub/ should not appear when recursive=False"
else
  pass=$((pass+1))
fi

echo
echo "=== 4. Context lines ==="
out=$($H --path fixtures/src --pattern "grep_me" --file_pattern "notes.txt" --recursive True --context 1 --max_results 100)
check "t4-rc" 0 $?
# context line before: "line one" on line 1, match on line 2
expect_output "t4-ctx-before" "$out" "notes.txt-1-line one"
# match line
expect_output "t4-match" "$out" "notes.txt:2: grep_me again here"
# context line after: line 3 "nothing on this line"
expect_output "t4-ctx-after" "$out" "notes.txt-3-nothing on this line"

echo
echo "=== 5. max_results truncation ==="
out=$($H --path fixtures/src --pattern grep_me --file_pattern "*" --recursive True --context 0 --max_results 2)
check "t5-rc" 0 $?
expect_output "t5-count" "$out" "Found 2 match(es)"
expect_output "t5-trunc" "$out" "Results truncated"

echo
echo "=== 6. No matches ==="
out=$($H --path fixtures/src --pattern "zzz_no_such_pattern" --file_pattern "*" --recursive True --context 0 --max_results 100)
check "t6-rc" 0 $?
expect_output "t6-msg" "$out" "No matches found for"

echo
echo "=== 7. Single file as path ==="
cp fixtures/src/app.py fixtures/single_file_test.txt
out=$($H --path fixtures/single_file_test.txt --pattern "grep_me" --file_pattern "*" --recursive True --context 0 --max_results 100)
check "t7-rc" 0 $?
expect_output "t7-count" "$out" "Found 3 match(es)"

echo
echo "=== 8. Binary file skip ==="
out=$($H --path fixtures/src --pattern "binary" --file_pattern "blob.bin" --recursive True --context 0 --max_results 100)
# grep should not crash on binary; it just skips it
check "t8-rc" 0 $?
expect_output "t8-msg" "$out" "No matches"

echo
echo "=== 9. Missing path -> error ==="
out=$($H --path fixtures/no_such_dir --pattern x --file_pattern "*" --recursive True --context 0 --max_results 100)
check "t9-rc" 1 $?
expect_output "t9-msg" "$out" "ERROR"

echo
echo "=== 10. Invalid regex -> error ==="
out=$($H --path fixtures/src --pattern "[invalid" --file_pattern "*" --recursive True --context 0 --max_results 100)
check "t10-rc" 1 $?
expect_output "t10-msg" "$out" "Invalid regular expression"

echo
echo "=== 11. Regex pattern with special chars ==="
out=$($H --path fixtures/src --pattern 'def grep_me' --file_pattern "*.py" --recursive True --context 0 --max_results 100)
check "t11-rc" 0 $?
expect_output "t11-count" "$out" "Found 1 match(es)"
expect_output "t11-line" "$out" "def grep_me"

summary
