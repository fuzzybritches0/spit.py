#!/bin/bash
source ../test_common.sh
trap remove_fixtures EXIT
rm -rf ./fixtures
bash ./create_fixtures.sh || exit 1
H="python3 ../harness.py"
D_FALSE="--use_regex False --max_replacements 0 --dry_run False"


echo "=== 1. Basic plain-text replace (all occurrences) ==="
cp fixtures/t01-basic.txt fixtures/t01-work.txt
out=$($H --path fixtures/t01-work.txt --find old_word --replace new_word ${D_FALSE})
check "t1-rc" 0 $?
expect_output "t1-msg" "$out" "Replaced 3 of 3 match(es)"
if [ "$(count_occurrences fixtures/t01-work.txt old_word)" -eq 0 ]; then
  pass=$((pass+1))
else
  fail=$((fail+1)); echo "FAIL: old_word still in file"
fi

echo
echo "=== 2. Regex: replace digit sequences ==="
cp fixtures/t02-regex.txt fixtures/t02-work.txt
out=$($H --path fixtures/t02-work.txt --find "[0-9]+" --replace NUMBER \
  --use_regex True --max_replacements 0 --dry_run False)
check "t2-rc" 0 $?
expect_output "t2-msg" "$out" "Replaced 5 of 5 match(es)"
remaining=$(grep -oP '[0-9]' fixtures/t02-work.txt | wc -l)
if [ "$remaining" -eq 0 ]; then
  pass=$((pass+1))
else
  fail=$((fail+1)); echo "FAIL: digits still in file ($remaining)"
fi

echo
echo "=== 3. max_replacements=2 ==="
cp fixtures/t03-multiple.txt fixtures/t03-work.txt
out=$($H --path fixtures/t03-work.txt --find repeated --replace changed \
  --use_regex False --max_replacements 2 --dry_run False)
check "t3-rc" 0 $?
expect_output "t3-msg" "$out" "Replaced 2 of 5 match(es)"
rem=$(count_occurrences fixtures/t03-work.txt repeated)
chg=$(count_occurrences fixtures/t03-work.txt changed)
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
cp fixtures/t04-no-match.txt fixtures/t04-work.txt
md5b=$(md5 fixtures/t04-work.txt)
out=$($H --path fixtures/t04-work.txt --find nonexistent_string --replace X ${D_FALSE})
check "t4-rc" 0 $?
expect_output "t4-msg" "$out" "No matches found for"
unchanged "t4" "$md5b" "$(md5 fixtures/t04-work.txt)"

echo
echo "=== 5. dry_run: reports matches, file unchanged ==="
cp fixtures/shared-dry-run.txt fixtures/t05-work.txt
md5b=$(md5 fixtures/t05-work.txt)
out=$($H --path fixtures/t05-work.txt --find unreplaced --replace replaced \
  --use_regex False --max_replacements 0 --dry_run True)
check "t5-rc" 0 $?
expect_output "t5-msg1" "$out" "DRY RUN"
expect_output "t5-msg2" "$out" "Found 3 match(es)"
expect_output "t5-msg3" "$out" "Would replace 3"
unchanged "t5" "$md5b" "$(md5 fixtures/t05-work.txt)"

echo
echo "=== 6. dry_run with max_replacements=2 ==="
cp fixtures/shared-dry-run.txt fixtures/t06-work.txt
md5b=$(md5 fixtures/t06-work.txt)
out=$($H --path fixtures/t06-work.txt --find unreplaced --replace replaced \
  --use_regex False --max_replacements 2 --dry_run True)
check "t6-rc" 0 $?
expect_output "t6-msg" "$out" "Would replace 2"
unchanged "t6" "$md5b" "$(md5 fixtures/t06-work.txt)"

echo
echo "=== 7. Complex regex: word boundary + capital ==="
cp fixtures/t07-complex-regex.txt fixtures/t07-work.txt
out=$($H --path fixtures/t07-work.txt --find "\\b[A-Z][a-z]+\\b" --replace NAME \
  --use_regex True --max_replacements 0 --dry_run False)
check "t7-rc" 0 $?
expect_output "t7-msg" "$out" "Replaced 4 of 4 match(es)"
remaining=$(grep -oP '[A-Z][a-z]+' fixtures/t07-work.txt | wc -l)
if [ "$remaining" -eq 0 ]; then
  pass=$((pass+1))
else
  fail=$((fail+1)); echo "FAIL: capitalized words still present"
fi

echo
echo "=== 8. Multi-line regex replace ==="
cp fixtures/t08-multiline.txt fixtures/t08-work.txt
out=$($H --path fixtures/t08-work.txt --find "line1\nline2" --replace "combined" \
  --use_regex True --max_replacements 0 --dry_run False)
check "t8-rc" 0 $?
expect_output "t8-msg" "$out" "Replaced 1 of 1 match(es)"
if grep -qF "combined" fixtures/t08-work.txt; then
  pass=$((pass+1))
else
  fail=$((fail+1)); echo "FAIL: 'combined' not found in file"
fi

echo
echo "=== 9. File not found -> error ==="
out=$($H --path fixtures/t09-no-such-file --find x --replace y ${D_FALSE})
check "t9-rc" 1 $?
expect_output "t9-msg" "$out" "ERROR"

summary
