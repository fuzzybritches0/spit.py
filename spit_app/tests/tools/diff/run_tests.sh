#!/bin/bash
source ../test_common.sh
H="python3 ../harness.py"

echo "=== 1. Unified diff (default) ==="
out=$($H --file1 fixtures/a.txt --file2 fixtures/b.txt --context 3 --output_format unified)
check "t1-rc" 0 $?
expect_output "t1-hdr" "$out" "---"
expect_output "t1-hunk" "$out" "@@ -1,5 +1,6 @@"
expect_output "t1-del" "$out" "-Line two"
expect_output "t1-add" "$out" "+Line two CHANGED"
expect_output "t1-add2" "$out" "+Line six"
expect_output "t1-sum" "$out" "1 line(s) added"

echo
echo "=== 2. Context diff ==="
out=$($H --file1 fixtures/a.txt --file2 fixtures/b.txt --context 1 --output_format context)
check "t2-rc" 0 $?
expect_output "t2-hdr" "$out" "***"
expect_output "t2-change" "$out" "! Line two CHANGED"

echo
echo "=== 3. Side-by-side ==="
out=$($H --file1 fixtures/a.txt --file2 fixtures/b.txt --context 3 --output_format side_by_side)
check "t3-rc" 0 $?
expect_output "t3-header" "$out" "(old)  vs"
expect_output "t3-marker" "$out" "[changed]"

echo
echo "=== 4. Identical files ==="
out=$($H --file1 fixtures/a.txt --file2 fixtures/c.txt --context 3 --output_format unified)
check "t4-rc" 0 $?
expect_output "t4-msg" "$out" "are identical"

echo
echo "=== 5. Missing file -> error ==="
out=$($H --file1 fixtures/a.txt --file2 fixtures/nope.txt --context 3 --output_format unified)
check "t5-rc" 1 $?
expect_output "t5-msg" "$out" "ERROR"

echo
echo "=== 6. Bad output_format -> error ==="
out=$($H --file1 fixtures/a.txt --file2 fixtures/b.txt --context 3 --output_format bogus)
check "t6-rc" 1 $?
expect_output "t6-msg" "$out" "invalid output_format"

echo
echo "=== 7. Directory as file -> error ==="
out=$($H --file1 fixtures/a.txt --file2 fixtures --context 3 --output_format unified)
check "t7-rc" 1 $?
expect_output "t7-msg" "$out" "ERROR"

echo
echo "=== 8. Summary line accurate (2 changed, 1 added) ==="
out=$($H --file1 fixtures/a.txt --file2 fixtures/b.txt --context 3 --output_format unified)
expect_output "t8-added" "$out" "1 line(s) added"
expect_output "t8-removed" "$out" "0 line(s) removed"
expect_output "t8-changed" "$out" "1 line(s) changed"

summary
