#!/bin/bash
source ../test_common.sh
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

cleanup() {
  rm -f work.txt work_no_nl.txt work_crlf.txt work_empty.txt
  rm -f /tmp/dl_*.txt /tmp/dl_roundtrip.diff /tmp/dl_rt.diff
}
trap cleanup EXIT

echo "=== 1. Delete a single line (start_line only) ==="
cp fixtures/original.txt work.txt
out=$(dl work.txt 3 None None False)
check "t1-rc" 0 $?
expect_output "t1-count" "$out" "Deleted 1 line(s)"
expect_output "t1-scope" "$out" "(line 3)"
expect_file "t1-bytes" work.txt fixtures/exp_del3.txt

echo
echo "=== 2. end_line equal to start_line is the same single line ==="
cp fixtures/original.txt work.txt
out=$(dl work.txt 3 3 None False)
check "t2-rc" 0 $?
expect_output "t2-scope" "$out" "(line 3)"
expect_file "t2-bytes" work.txt fixtures/exp_del3.txt

echo
echo "=== 3. Delete an inclusive range (2-4) ==="
cp fixtures/original.txt work.txt
out=$(dl work.txt 2 4 None False)
check "t3-rc" 0 $?
expect_output "t3-count" "$out" "Deleted 3 line(s)"
expect_output "t3-scope" "$out" "(lines 2-4)"
expect_file "t3-bytes" work.txt fixtures/exp_del_range.txt

echo
echo "=== 4. Delete a range reaching the last line (4-5) ==="
cp fixtures/original.txt work.txt
out=$(dl work.txt 4 5 None False)
check "t4-rc" 0 $?
expect_file "t4-bytes" work.txt fixtures/exp_del_to_end.txt

echo
echo "=== 5. Delete the first line ==="
cp fixtures/original.txt work.txt
out=$(dl work.txt 1 None None False)
check "t5-rc" 0 $?
expect_output "t5-scope" "$out" "(line 1)"
expect_file "t5-bytes" work.txt fixtures/exp_del_top.txt

echo
echo "=== 6. Delete every line matching a pattern ==="
cp fixtures/original.txt work.txt
out=$(dl work.txt None None TODO False)
check "t6-rc" 0 $?
expect_output "t6-count" "$out" "Deleted 2 line(s)"
expect_output "t6-scope" "$out" "(matching \`TODO\`)"
expect_file "t6-bytes" work.txt fixtures/exp_del_pattern.txt

echo
echo "=== 7. Pattern restricted to a range deletes only inside it ==="
cp fixtures/original.txt work.txt
out=$(dl work.txt 2 3 TODO False)
check "t7-rc" 0 $?
expect_output "t7-count" "$out" "Deleted 1 line(s)"
expect_output "t7-scope" "$out" "(lines 2-3 matching \`TODO\`)"
expect_file "t7-bytes" work.txt fixtures/exp_del_pattern_range.txt

echo
echo "=== 8. Anchored patterns ^ and \$ ==="
cp fixtures/original.txt work.txt
out=$(dl work.txt None None '^Line' False)
check "t8a-rc" 0 $?
expect_file "t8a-bytes" work.txt fixtures/exp_del_anchored.txt
cp fixtures/original.txt work.txt
out=$(dl work.txt None None 'five$' False)
check "t8b-rc" 0 $?
tail -1 work.txt | grep -qF "TODO: fix that" && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: line 5 survived 'five\$'"; }

echo
echo "=== 9. Delete all lines of the file ==="
cp fixtures/original.txt work.txt
out=$(dl work.txt 1 5 None False)
check "t9-rc" 0 $?
expect_output "t9-remaining" "$out" "File now has 0 line(s)."
[ ! -s work.txt ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: file not empty"; }

echo
echo "=== 10. Pattern '.' is a regex (matches every line) ==="
cp fixtures/original.txt work.txt
out=$(dl work.txt None None . False)
check "t10-rc" 0 $?
expect_output "t10-count" "$out" "Deleted 5 line(s)"
[ ! -s work.txt ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: file not empty"; }

echo
echo "=== 11. dry_run reports a diff and leaves the file alone ==="
cp fixtures/original.txt work.txt
md5b=$(md5 work.txt)
out=$(dl work.txt 2 4 None True)
check "t11-rc" 0 $?
expect_output "t11-dry" "$out" "DRY RUN"
expect_output "t11-would" "$out" "would be deleted"
expect_output "t11-have" "$out" "would have 2 line(s)"
expect_output "t11-from" "$out" "--- work.txt"
expect_output "t11-to" "$out" "+++ work.txt (deleted)"
echo "$out" | grep -q "^@@" && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: no @@ hunk header"; }
unchanged "t11-md5" "$md5b" "$(md5 work.txt)"

echo
echo "=== 12. No match with a pattern is not an error ==="
cp fixtures/original.txt work.txt
md5b=$(md5 work.txt)
out=$(dl work.txt None None NOTHING_HERE False)
check "t12-rc" 0 $?
expect_output "t12-msg" "$out" "No lines matched"
unchanged "t12-md5" "$md5b" "$(md5 work.txt)"

echo
echo "=== 13. Pattern that does not match inside the given range ==="
cp fixtures/original.txt work.txt
md5b=$(md5 work.txt)
out=$(dl work.txt 2 2 '^Line' False)
check "t13-rc" 0 $?
expect_output "t13-msg" "$out" "No lines matched"
unchanged "t13-md5" "$md5b" "$(md5 work.txt)"

echo
echo "=== 14. Invalid regex ==="
cp fixtures/original.txt work.txt
out=$(dl work.txt None None '((' False)
check "t14-rc" 1 $?
expect_output "t14-msg" "$out" "Invalid regex pattern"

echo
echo "=== 15. Errors ==="
cp fixtures/original.txt work.txt
out=$(dl work.txt None None "" False)
check "t15a-empty-pattern" 1 $?
expect_output "t15a-msg" "$out" "Pattern is empty"

out=$(dl work.txt None None None False)
check "t15b-nothing" 1 $?
expect_output "t15b-msg" "$out" "Nothing to delete"

out=$(dl work.txt None 4 None False)
check "t15c-end-only" 1 $?
expect_output "t15c-msg" "$out" "requires \`start_line\`"

out=$(dl work.txt 4 2 None False)
check "t15d-reversed" 1 $?
expect_output "t15d-msg" "$out" "is before"

out=$(dl work.txt 0 None None False)
check "t15e-start-0" 1 $?
expect_output "t15e-msg" "$out" "out of range"

out=$(dl work.txt 6 None None False)
check "t15f-start-6" 1 $?
expect_output "t15f-msg" "$out" "out of range"

out=$(dl work.txt 4 6 None False)
check "t15g-end-6" 1 $?
expect_output "t15g-msg" "$out" "out of range"
unchanged "t15g-untouched" "$(md5 fixtures/original.txt)" "$(md5 work.txt)"

out=$(dl work.txt abc None None False)
check "t15h-start-nonint" 1 $?
expect_output "t15h-msg" "$out" "must be an integer"

out=$(dl work.txt 2 xyz None False)
check "t15i-end-nonint" 1 $?
expect_output "t15i-msg" "$out" "must be an integer"

out=$(dl /tmp/dl_no_such_file 2 None None False)
check "t15j-missing" 1 $?
expect_output "t15j-msg" "$out" "ERROR"

out=$(dl fixtures None None TODO False)
check "t15k-directory" 1 $?
expect_output "t15k-msg" "$out" "not a file"

echo
echo "=== 16. Empty file ==="
: > work_empty.txt
md5b=$(md5 work_empty.txt)
out=$(dl work_empty.txt None None TODO False)
check "t16a-pattern" 0 $?
expect_output "t16a-msg" "$out" "No lines matched"
unchanged "t16a-untouched" "$md5b" "$(md5 work_empty.txt)"

out=$(dl work_empty.txt 1 None None False)
check "t16b-line" 1 $?
expect_output "t16b-msg" "$out" "empty"

echo
echo "=== 17. No trailing newline is preserved ==="
cp fixtures/original_no_nl.txt work_no_nl.txt
dl work_no_nl.txt 2 None None False > /dev/null
expect_file "t17a-mid" work_no_nl.txt fixtures/exp_nonl_mid.txt
cp fixtures/original_no_nl.txt work_no_nl.txt
dl work_no_nl.txt 3 None None False > /dev/null
expect_file "t17b-last" work_no_nl.txt fixtures/exp_nonl_last.txt
cp fixtures/original_no_nl.txt work_no_nl.txt
dl work_no_nl.txt 1 None None False > /dev/null
expect_file "t17c-first" work_no_nl.txt fixtures/exp_nonl_first.txt
cp fixtures/original_no_nl.txt work_no_nl.txt
dl work_no_nl.txt 1 3 None False > /dev/null
[ ! -s work_no_nl.txt ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: file not empty"; }

echo
echo "=== 18. CRLF line endings survive ==="
cp fixtures/original_crlf.txt work_crlf.txt
out=$(dl work_crlf.txt 2 None None False)
check "t18a-rc" 0 $?
expect_file "t18a-bytes" work_crlf.txt fixtures/exp_crlf_del2.txt
cp fixtures/original_crlf.txt work_crlf.txt
dl work_crlf.txt 2 3 None False > /dev/null
expect_file "t18b-bytes" work_crlf.txt fixtures/exp_crlf_del_range.txt
cp fixtures/original_crlf.txt work_crlf.txt
dl work_crlf.txt None None two False > /dev/null
expect_file "t18c-pattern-bytes" work_crlf.txt fixtures/exp_crlf_del2.txt
count=$(grep -c $'\r' work_crlf.txt)
[ "$count" -eq 3 ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: CRLF count is $count, expected 3"; }

echo
echo "=== 19. dry_run diff is pasteable into the patch tool ==="
cp fixtures/original.txt work.txt
cp fixtures/original.txt /tmp/dl_roundtrip_target.txt
dl work.txt None None TODO False > /dev/null
dl /tmp/dl_roundtrip_target.txt None None TODO True | extract_diff > /tmp/dl_roundtrip.diff
[ -s /tmp/dl_roundtrip.diff ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: empty extracted diff"; }
out=$(cd "$patch_dir" && python3 ../harness.py --path /tmp/dl_roundtrip_target.txt \
      --diff "$(cat /tmp/dl_roundtrip.diff)" --reverse False --dry_run False)
check "t19-patch-rc" 0 $?
expect_output "t19-patch-applied" "$out" "applied"
expect_file "t19-roundtrip" /tmp/dl_roundtrip_target.txt work.txt

echo
echo "=== 20. dry_run of a whole-file delete and of a range delete ==="
cp fixtures/original.txt work.txt
md5b=$(md5 work.txt)
out=$(dl work.txt 1 5 None True)
check "t20a-rc" 0 $?
expect_output "t20a-count" "$out" "5 line(s) would be deleted"
expect_output "t20a-have" "$out" "File would have 0 line(s)"
unchanged "t20a-md5" "$md5b" "$(md5 work.txt)"
cp fixtures/original.txt work.txt
out=$(dl work.txt 2 3 None True)
check "t20b-rc" 0 $?
expect_output "t20b-would" "$out" "2 line(s) would be deleted (lines 2-3)"

echo
echo "=== 21. Blank lines are ordinary lines ==="
cp fixtures/blank_lines.txt work.txt
out=$(dl work.txt None None '^$' False)
check "t21a-rc" 0 $?
expect_output "t21a-count" "$out" "Deleted 5 line(s)"
expect_file "t21a-bytes" work.txt fixtures/exp_blank_pattern.txt
cp fixtures/blank_lines.txt work.txt
dl work.txt 3 8 None False > /dev/null
expect_file "t21b-bytes" work.txt fixtures/exp_blank_range.txt
cp fixtures/blank_lines.txt work.txt
dl work.txt 1 None None False > /dev/null
printf '\nalpha\n\nbeta\n\n\ngamma\n' > /tmp/dl_exp_blank_first.txt
expect_file "t21c-bytes" work.txt /tmp/dl_exp_blank_first.txt

echo
echo "=== 22. dry_run diff round-trips through patch for tricky shapes ==="
roundtrip() {
  local src="$1" start="$2" end="$3" pat="$4" label="$5"
  cp "$src" work.txt
  cp "$src" /tmp/dl_rt.txt
  dl /tmp/dl_rt.txt "$start" "$end" "$pat" True | extract_diff > /tmp/dl_rt.diff
  [ -s /tmp/dl_rt.diff ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: $label empty diff"; }
  dl work.txt "$start" "$end" "$pat" False > /dev/null
  ( cd "$patch_dir" && python3 ../harness.py --path /tmp/dl_rt.txt \
    --diff "$(cat /tmp/dl_rt.diff)" --reverse False --dry_run False ) > /dev/null
  check "$label-patch-rc" 0 $?
  expect_file "$label" /tmp/dl_rt.txt work.txt
}
roundtrip fixtures/blank_lines.txt None None '^$' t22a-blank-pattern
roundtrip fixtures/blank_lines.txt 3 8 None t22b-blank-range
roundtrip fixtures/blank_lines.txt 1 None None t22c-blank-first
roundtrip fixtures/original_no_nl.txt 1 2 None t22d-nonl-first
roundtrip fixtures/original_no_nl.txt 3 None None t22e-nonl-last
roundtrip fixtures/original_crlf.txt 2 3 None t22f-crlf-range
roundtrip fixtures/original.txt None None TODO t22g-scattered-pattern

echo
echo "=== 23. dry_run marks a missing trailing newline (and only then) ==="
cp fixtures/original_no_nl.txt work_no_nl.txt
out=$(dl work_no_nl.txt 2 None None True)
check "t23a-rc" 0 $?
expect_output "t23a-marker" "$out" "\ No newline at end of file"
cp fixtures/original.txt work.txt
out=$(dl work.txt 3 None None True)
check "t23b-rc" 0 $?
echo "$out" | grep -qF "No newline" && { fail=$((fail+1)); echo "FAIL: marker on a file that ends with a newline"; } || pass=$((pass+1))

summary
