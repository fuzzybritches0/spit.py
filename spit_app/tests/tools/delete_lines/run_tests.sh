#!/bin/bash
cd "$(dirname ${0})"
source ../test_common.sh
trap remove_fixtures EXIT
rm -rf ./fixtures
bash ./create_fixtures.sh || exit 1
FIXTURES=$PWD/fixtures
H="python3 ../harness.py"
patch_dir=$(cd ../patch && pwd)

# dl PATH START END PATTERN DRY
dl() {
  $H --path "$1" --start_line "$2" --end_line "$3" --pattern "$4" --dry_run "$5"
}

# Keep only the unified diff of a dry_run report (drops the header and the summary)
extract_diff() {
  awk '/^--- /{f=1} /^[0-9]+ line\(s\) would be deleted/{exit} f{h[++n]=$0}
       END{while(n>0 && h[n]=="") n--; for(i=1;i<=n;i++) print h[i]}'
}


echo "=== 1. Delete a single line (start_line only) ==="
cp fixtures/shared-original.txt fixtures/t01-work.txt
out=$(dl fixtures/t01-work.txt 3 None None False)
check "t1-rc" 0 $?
expect_output "t1-count" "$out" "Deleted 1 line(s)"
expect_output "t1-scope" "$out" "(line 3)"
expect_file "t1-bytes" fixtures/t01-work.txt fixtures/shared-exp-del3.txt

echo
echo "=== 2. end_line equal to start_line is the same single line ==="
cp fixtures/shared-original.txt fixtures/t02-work.txt
out=$(dl fixtures/t02-work.txt 3 3 None False)
check "t2-rc" 0 $?
expect_output "t2-scope" "$out" "(line 3)"
expect_file "t2-bytes" fixtures/t02-work.txt fixtures/shared-exp-del3.txt

echo
echo "=== 3. Delete an inclusive range (2-4) ==="
cp fixtures/shared-original.txt fixtures/t03-work.txt
out=$(dl fixtures/t03-work.txt 2 4 None False)
check "t3-rc" 0 $?
expect_output "t3-count" "$out" "Deleted 3 line(s)"
expect_output "t3-scope" "$out" "(lines 2-4)"
expect_file "t3-bytes" fixtures/t03-work.txt fixtures/t03-exp-del-range.txt

echo
echo "=== 4. Delete a range reaching the last line (4-5) ==="
cp fixtures/shared-original.txt fixtures/t04-work.txt
out=$(dl fixtures/t04-work.txt 4 5 None False)
check "t4-rc" 0 $?
expect_file "t4-bytes" fixtures/t04-work.txt fixtures/t04-exp-del-to-end.txt

echo
echo "=== 5. Delete the first line ==="
cp fixtures/shared-original.txt fixtures/t05-work.txt
out=$(dl fixtures/t05-work.txt 1 None None False)
check "t5-rc" 0 $?
expect_output "t5-scope" "$out" "(line 1)"
expect_file "t5-bytes" fixtures/t05-work.txt fixtures/t05-exp-del-top.txt

echo
echo "=== 6. Delete every line matching a pattern ==="
cp fixtures/shared-original.txt fixtures/t06-work.txt
out=$(dl fixtures/t06-work.txt None None TODO False)
check "t6-rc" 0 $?
expect_output "t6-count" "$out" "Deleted 2 line(s)"
expect_output "t6-scope" "$out" "(matching \`TODO\`)"
expect_file "t6-bytes" fixtures/t06-work.txt fixtures/t06-exp-del-pattern.txt

echo
echo "=== 7. Pattern restricted to a range deletes only inside it ==="
cp fixtures/shared-original.txt fixtures/t07-work.txt
out=$(dl fixtures/t07-work.txt 2 3 TODO False)
check "t7-rc" 0 $?
expect_output "t7-count" "$out" "Deleted 1 line(s)"
expect_output "t7-scope" "$out" "(lines 2-3 matching \`TODO\`)"
expect_file "t7-bytes" fixtures/t07-work.txt fixtures/t07-exp-del-pattern-range.txt

echo
echo "=== 8. Anchored patterns ^ and \$ ==="
cp fixtures/shared-original.txt fixtures/t08-work.txt
out=$(dl fixtures/t08-work.txt None None '^Line' False)
check "t8a-rc" 0 $?
expect_file "t8a-bytes" fixtures/t08-work.txt fixtures/t08-exp-del-anchored.txt
cp fixtures/shared-original.txt fixtures/t08-work.txt
out=$(dl fixtures/t08-work.txt None None 'five$' False)
check "t8b-rc" 0 $?
tail -1 fixtures/t08-work.txt | grep -qF "TODO: fix that" && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: line 5 survived 'five\$'"; }

echo
echo "=== 9. Delete all lines of the file ==="
cp fixtures/shared-original.txt fixtures/t09-work.txt
out=$(dl fixtures/t09-work.txt 1 5 None False)
check "t9-rc" 0 $?
expect_output "t9-remaining" "$out" "File now has 0 line(s)."
[ ! -s fixtures/t09-work.txt ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: file not empty"; }

echo
echo "=== 10. Pattern '.' is a regex (matches every line) ==="
cp fixtures/shared-original.txt fixtures/t10-work.txt
out=$(dl fixtures/t10-work.txt None None . False)
check "t10-rc" 0 $?
expect_output "t10-count" "$out" "Deleted 5 line(s)"
[ ! -s fixtures/t10-work.txt ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: file not empty"; }

echo
echo "=== 11. dry_run reports a diff and leaves the file alone ==="
cp fixtures/shared-original.txt fixtures/t11-work.txt
md5b=$(md5 fixtures/t11-work.txt)
out=$(dl fixtures/t11-work.txt 2 4 None True)
check "t11-rc" 0 $?
expect_output "t11-dry" "$out" "DRY RUN"
expect_output "t11-would" "$out" "would be deleted"
expect_output "t11-have" "$out" "would have 2 line(s)"
expect_output "t11-from" "$out" "--- fixtures/t11-work.txt"
expect_output "t11-to" "$out" "+++ fixtures/t11-work.txt (deleted)"
echo "$out" | grep -q "^@@" && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: no @@ hunk header"; }
unchanged "t11-md5" "$md5b" "$(md5 fixtures/t11-work.txt)"

echo
echo "=== 12. No match with a pattern is not an error ==="
cp fixtures/shared-original.txt fixtures/t12-work.txt
md5b=$(md5 fixtures/t12-work.txt)
out=$(dl fixtures/t12-work.txt None None NOTHING_HERE False)
check "t12-rc" 0 $?
expect_output "t12-msg" "$out" "No lines matched"
unchanged "t12-md5" "$md5b" "$(md5 fixtures/t12-work.txt)"

echo
echo "=== 13. Pattern that does not match inside the given range ==="
cp fixtures/shared-original.txt fixtures/t13-work.txt
md5b=$(md5 fixtures/t13-work.txt)
out=$(dl fixtures/t13-work.txt 2 2 '^Line' False)
check "t13-rc" 0 $?
expect_output "t13-msg" "$out" "No lines matched"
unchanged "t13-md5" "$md5b" "$(md5 fixtures/t13-work.txt)"

echo
echo "=== 14. Invalid regex ==="
cp fixtures/shared-original.txt fixtures/t14-work.txt
out=$(dl fixtures/t14-work.txt None None '((' False)
check "t14-rc" 1 $?
expect_output "t14-msg" "$out" "Invalid regex pattern"

echo
echo "=== 15. Errors ==="
cp fixtures/shared-original.txt fixtures/t15-work.txt
out=$(dl fixtures/t15-work.txt None None "" False)
check "t15a-empty-pattern" 1 $?
expect_output "t15a-msg" "$out" "Pattern is empty"

out=$(dl fixtures/t15-work.txt None None None False)
check "t15b-nothing" 1 $?
expect_output "t15b-msg" "$out" "Nothing to delete"

out=$(dl fixtures/t15-work.txt None 4 None False)
check "t15c-end-only" 1 $?
expect_output "t15c-msg" "$out" "requires \`start_line\`"

out=$(dl fixtures/t15-work.txt 4 2 None False)
check "t15d-reversed" 1 $?
expect_output "t15d-msg" "$out" "is before"

out=$(dl fixtures/t15-work.txt 0 None None False)
check "t15e-start-0" 1 $?
expect_output "t15e-msg" "$out" "out of range"

out=$(dl fixtures/t15-work.txt 6 None None False)
check "t15f-start-6" 1 $?
expect_output "t15f-msg" "$out" "out of range"

out=$(dl fixtures/t15-work.txt 4 6 None False)
check "t15g-end-6" 1 $?
expect_output "t15g-msg" "$out" "out of range"
unchanged "t15g-untouched" "$(md5 fixtures/shared-original.txt)" "$(md5 fixtures/t15-work.txt)"

out=$(dl fixtures/t15-work.txt abc None None False)
check "t15h-start-nonint" 1 $?
expect_output "t15h-msg" "$out" "must be an integer"

out=$(dl fixtures/t15-work.txt 2 xyz None False)
check "t15i-end-nonint" 1 $?
expect_output "t15i-msg" "$out" "must be an integer"

out=$(dl fixtures/t15-no-such-file 2 None None False)
check "t15j-missing" 1 $?
expect_output "t15j-msg" "$out" "ERROR"

out=$(dl fixtures None None TODO False)
check "t15k-directory" 1 $?
expect_output "t15k-msg" "$out" "not a file"

echo
echo "=== 16. Empty file ==="
: > fixtures/t16-work-empty.txt
md5b=$(md5 fixtures/t16-work-empty.txt)
out=$(dl fixtures/t16-work-empty.txt None None TODO False)
check "t16a-pattern" 0 $?
expect_output "t16a-msg" "$out" "No lines matched"
unchanged "t16a-untouched" "$md5b" "$(md5 fixtures/t16-work-empty.txt)"

out=$(dl fixtures/t16-work-empty.txt 1 None None False)
check "t16b-line" 1 $?
expect_output "t16b-msg" "$out" "empty"

echo
echo "=== 17. No trailing newline is preserved ==="
cp fixtures/shared-original-no-nl.txt fixtures/t17-work-no-nl.txt
dl fixtures/t17-work-no-nl.txt 2 None None False > /dev/null
expect_file "t17a-mid" fixtures/t17-work-no-nl.txt fixtures/t17-exp-nonl-mid.txt
cp fixtures/shared-original-no-nl.txt fixtures/t17-work-no-nl.txt
dl fixtures/t17-work-no-nl.txt 3 None None False > /dev/null
expect_file "t17b-last" fixtures/t17-work-no-nl.txt fixtures/t17-exp-nonl-last.txt
cp fixtures/shared-original-no-nl.txt fixtures/t17-work-no-nl.txt
dl fixtures/t17-work-no-nl.txt 1 None None False > /dev/null
expect_file "t17c-first" fixtures/t17-work-no-nl.txt fixtures/t17-exp-nonl-first.txt
cp fixtures/shared-original-no-nl.txt fixtures/t17-work-no-nl.txt
dl fixtures/t17-work-no-nl.txt 1 3 None False > /dev/null
[ ! -s fixtures/t17-work-no-nl.txt ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: file not empty"; }

echo
echo "=== 18. CRLF line endings survive ==="
cp fixtures/shared-original-crlf.txt fixtures/t18-work-crlf.txt
out=$(dl fixtures/t18-work-crlf.txt 2 None None False)
check "t18a-rc" 0 $?
expect_file "t18a-bytes" fixtures/t18-work-crlf.txt fixtures/t18-exp-crlf-del2.txt
cp fixtures/shared-original-crlf.txt fixtures/t18-work-crlf.txt
dl fixtures/t18-work-crlf.txt 2 3 None False > /dev/null
expect_file "t18b-bytes" fixtures/t18-work-crlf.txt fixtures/t18-exp-crlf-del-range.txt
cp fixtures/shared-original-crlf.txt fixtures/t18-work-crlf.txt
dl fixtures/t18-work-crlf.txt None None two False > /dev/null
expect_file "t18c-pattern-bytes" fixtures/t18-work-crlf.txt fixtures/t18-exp-crlf-del2.txt
count=$(grep -c $'\r' fixtures/t18-work-crlf.txt)
[ "$count" -eq 3 ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: CRLF count is $count, expected 3"; }

echo
echo "=== 19. dry_run diff is pasteable into the patch tool ==="
cp fixtures/shared-original.txt fixtures/t19-work.txt
cp fixtures/shared-original.txt $FIXTURES/t19-rt-target.txt
dl fixtures/t19-work.txt None None TODO False > /dev/null
dl $FIXTURES/t19-rt-target.txt None None TODO True | extract_diff > $FIXTURES/t19-rt.diff
[ -s $FIXTURES/t19-rt.diff ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: empty extracted diff"; }
out=$(cd "$patch_dir" && python3 ../harness.py --path $FIXTURES/t19-rt-target.txt \
      --diff "$(cat $FIXTURES/t19-rt.diff)" --reverse False --dry_run False)
check "t19-patch-rc" 0 $?
expect_output "t19-patch-applied" "$out" "applied"
expect_file "t19-roundtrip" $FIXTURES/t19-rt-target.txt fixtures/t19-work.txt

echo
echo "=== 20. dry_run of a whole-file delete and of a range delete ==="
cp fixtures/shared-original.txt fixtures/t20-work.txt
md5b=$(md5 fixtures/t20-work.txt)
out=$(dl fixtures/t20-work.txt 1 5 None True)
check "t20a-rc" 0 $?
expect_output "t20a-count" "$out" "5 line(s) would be deleted"
expect_output "t20a-have" "$out" "File would have 0 line(s)"
unchanged "t20a-md5" "$md5b" "$(md5 fixtures/t20-work.txt)"
cp fixtures/shared-original.txt fixtures/t20-work.txt
out=$(dl fixtures/t20-work.txt 2 3 None True)
check "t20b-rc" 0 $?
expect_output "t20b-would" "$out" "2 line(s) would be deleted (lines 2-3)"

echo
echo "=== 21. Blank lines are ordinary lines ==="
cp fixtures/shared-blank-lines.txt fixtures/t21-work.txt
out=$(dl fixtures/t21-work.txt None None '^$' False)
check "t21a-rc" 0 $?
expect_output "t21a-count" "$out" "Deleted 5 line(s)"
expect_file "t21a-bytes" fixtures/t21-work.txt fixtures/t21-exp-blank-pattern.txt
cp fixtures/shared-blank-lines.txt fixtures/t21-work.txt
dl fixtures/t21-work.txt 3 8 None False > /dev/null
expect_file "t21b-bytes" fixtures/t21-work.txt fixtures/t21-exp-blank-range.txt
cp fixtures/shared-blank-lines.txt fixtures/t21-work.txt
dl fixtures/t21-work.txt 1 None None False > /dev/null
printf '\nalpha\n\nbeta\n\n\ngamma\n' > fixtures/t21-exp-blank-first.txt
expect_file "t21c-bytes" fixtures/t21-work.txt fixtures/t21-exp-blank-first.txt

echo
echo "=== 22. dry_run diff round-trips through patch for tricky shapes ==="
roundtrip() {
  local src="$1" start="$2" end="$3" pat="$4" label="$5"
  cp "$src" fixtures/t22-work.txt
  cp "$src" $FIXTURES/t22-rt.txt
  dl $FIXTURES/t22-rt.txt "$start" "$end" "$pat" True | extract_diff > $FIXTURES/t22-rt.diff
  [ -s $FIXTURES/t22-rt.diff ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: $label empty diff"; }
  dl fixtures/t22-work.txt "$start" "$end" "$pat" False > /dev/null
  ( cd "$patch_dir" && python3 ../harness.py --path $FIXTURES/t22-rt.txt \
    --diff "$(cat $FIXTURES/t22-rt.diff)" --reverse False --dry_run False ) > /dev/null
  check "$label-patch-rc" 0 $?
  expect_file "$label" $FIXTURES/t22-rt.txt fixtures/t22-work.txt
}
roundtrip fixtures/shared-blank-lines.txt None None '^$' t22a-blank-pattern
roundtrip fixtures/shared-blank-lines.txt 3 8 None t22b-blank-range
roundtrip fixtures/shared-blank-lines.txt 1 None None t22c-blank-first
roundtrip fixtures/shared-original-no-nl.txt 1 2 None t22d-nonl-first
roundtrip fixtures/shared-original-no-nl.txt 3 None None t22e-nonl-last
roundtrip fixtures/shared-original-crlf.txt 2 3 None t22f-crlf-range
roundtrip fixtures/shared-original.txt None None TODO t22g-scattered-pattern

echo
echo "=== 23. dry_run marks a missing trailing newline (and only then) ==="
cp fixtures/shared-original-no-nl.txt fixtures/t23-work-no-nl.txt
out=$(dl fixtures/t23-work-no-nl.txt 2 None None True)
check "t23a-rc" 0 $?
expect_output "t23a-marker" "$out" "\ No newline at end of file"
cp fixtures/shared-original.txt fixtures/t23-work.txt
out=$(dl fixtures/t23-work.txt 3 None None True)
check "t23b-rc" 0 $?
echo "$out" | grep -qF "No newline" && { fail=$((fail+1)); echo "FAIL: marker on a file that ends with a newline"; } || pass=$((pass+1))

summary
