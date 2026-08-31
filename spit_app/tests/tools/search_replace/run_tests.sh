#!/bin/bash
source ../test_common.sh
trap remove_fixtures EXIT
rm -rf ./fixtures
bash ./create_fixtures.sh || exit 1
H="python3 ../harness.py"
D_FALSE="--use_regex False --max_replacements 0 --dry_run False"


echo "=== 1. Basic plain-text replace (all occurrences) ==="
cp fixtures/basic.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --find old_word --replace new_word ${D_FALSE})
check "t1-rc" 0 $?
expect_output "t1-msg" "$out" "Replaced 3 of 3 match(es)"
if [ "$(count_occurrences fixtures/work.txt old_word)" -eq 0 ]; then
  pass=$((pass+1))
else
  fail=$((fail+1)); echo "FAIL: old_word still in file"
fi

echo
echo "=== 2. Regex: replace digit sequences ==="
cp fixtures/regex.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --find "[0-9]+" --replace NUMBER \
  --use_regex True --max_replacements 0 --dry_run False)
check "t2-rc" 0 $?
expect_output "t2-msg" "$out" "Replaced 5 of 5 match(es)"
remaining=$(grep -oP '[0-9]' fixtures/work.txt | wc -l)
if [ "$remaining" -eq 0 ]; then
  pass=$((pass+1))
else
  fail=$((fail+1)); echo "FAIL: digits still in file ($remaining)"
fi

echo
echo "=== 3. max_replacements=2 ==="
cp fixtures/multiple.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --find repeated --replace changed \
  --use_regex False --max_replacements 2 --dry_run False)
check "t3-rc" 0 $?
expect_output "t3-msg" "$out" "Replaced 2 of 5 match(es)"
rem=$(count_occurrences fixtures/work.txt repeated)
chg=$(count_occurrences fixtures/work.txt changed)
if [ "$rem" -eq 3 ]; then
  pass=$((pass+1))
else
  fail=$((fail+1)); echo "FAIL: expected 3 'repeated' remaining, got $rem"
fi
if [ "$chg" -eq 2 ]; then
  pass=$((pass+1))
else
  fail=$((fail+1)); echo "FAIL: expected 2 'changed', got $chg"
fi

echo
echo "=== 4. No matches found ==="
cp fixtures/no_match.txt fixtures/work.txt
md5b=$(md5 fixtures/work.txt)
out=$($H --path fixtures/work.txt --find nonexistent_string --replace X ${D_FALSE})
check "t4-rc" 0 $?
expect_output "t4-msg" "$out" "No matches found for"
unchanged "t4" "$md5b" "$(md5 fixtures/work.txt)"

echo
echo "=== 5. dry_run: reports matches, file unchanged ==="
cp fixtures/dry_run.txt fixtures/work.txt
md5b=$(md5 fixtures/work.txt)
out=$($H --path fixtures/work.txt --find unreplaced --replace replaced \
  --use_regex False --max_replacements 0 --dry_run True)
check "t5-rc" 0 $?
expect_output "t5-msg1" "$out" "DRY RUN"
expect_output "t5-msg2" "$out" "Found 3 match(es)"
expect_output "t5-msg3" "$out" "Would replace 3"
unchanged "t5" "$md5b" "$(md5 fixtures/work.txt)"

echo
echo "=== 6. dry_run with max_replacements=2 ==="
cp fixtures/dry_run.txt fixtures/work.txt
md5b=$(md5 fixtures/work.txt)
out=$($H --path fixtures/work.txt --find unreplaced --replace replaced \
  --use_regex False --max_replacements 2 --dry_run True)
check "t6-rc" 0 $?
expect_output "t6-msg" "$out" "Would replace 2"
unchanged "t6" "$md5b" "$(md5 fixtures/work.txt)"

echo
echo "=== 7. Complex regex: word boundary + capital ==="
cp fixtures/complex_regex.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --find "\\b[A-Z][a-z]+\\b" --replace NAME \
  --use_regex True --max_replacements 0 --dry_run False)
check "t7-rc" 0 $?
expect_output "t7-msg" "$out" "Replaced 4 of 4 match(es)"
remaining=$(grep -oP '[A-Z][a-z]+' fixtures/work.txt | wc -l)
if [ "$remaining" -eq 0 ]; then
  pass=$((pass+1))
else
  fail=$((fail+1)); echo "FAIL: capitalized words still present"
fi

echo
echo "=== 8. Multi-line regex replace ==="
cp fixtures/multiline.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --find "line1\nline2" --replace "combined" \
  --use_regex True --max_replacements 0 --dry_run False)
check "t8-rc" 0 $?
expect_output "t8-msg" "$out" "Replaced 1 of 1 match(es)"
if grep -qF "combined" fixtures/work.txt; then
  pass=$((pass+1))
else
  fail=$((fail+1)); echo "FAIL: 'combined' not found in file"
fi

echo
echo "=== 9. File not found -> error ==="
out=$($H --path fixtures/no_such_file --find x --replace y ${D_FALSE})
check "t9-rc" 1 $?
expect_output "t9-msg" "$out" "ERROR"

summary
