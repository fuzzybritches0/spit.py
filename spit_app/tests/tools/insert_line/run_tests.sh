#!/bin/bash
source ../test_common.sh
trap remove_fixtures EXIT
rm -rf ./fixtures
bash ./create_fixtures.sh || exit 1
FIXTURES=$PWD/fixtures
H="python3 ../harness.py"
# Only fixed args go in the base; line_number and dry_run are set per-test
B="--after_line None --dry_run False"
patch_dir=$(cd ../patch && pwd)

# il PATH CONTENT LINE_NUMBER DRY — always passes every arg, the harness reads
# each flag only once (first occurrence wins)
il() {
  $H --path "$1" --content "$2" --line_number "$3" --after_line None --dry_run "$4"
}

# Keep only the unified diff of a dry_run report (drops the header and the summary)
extract_diff() {
  awk '/^--- /{f=1} /^[0-9]+ line\(s\) would be inserted/{exit} f{h[++n]=$0}
       END{while(n>0 && h[n]=="") n--; for(i=1;i<=n;i++) print h[i]}'
}

# Apply the dry_run preview with the patch tool and compare against the real result
roundtrip() {
  local src="$1" content="$2" line="$3" label="$4"
  cp "$src" fixtures/work.txt
  cp "$src" $FIXTURES/il_rt.txt
  il $FIXTURES/il_rt.txt "$content" "$line" True | extract_diff > $FIXTURES/il_rt.diff
  [ -s $FIXTURES/il_rt.diff ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: $label empty diff"; }
  il fixtures/work.txt "$content" "$line" False > /dev/null
  ( cd "$patch_dir" && python3 ../harness.py --path $FIXTURES/il_rt.txt \
    --diff "$(cat $FIXTURES/il_rt.diff)" --reverse False --dry_run False ) > /dev/null
  check "$label-patch-rc" 0 $?
  expect_file "$label" $FIXTURES/il_rt.txt fixtures/work.txt
}


echo "=== 1. Insert in the middle (line_number=3) ==="
cp fixtures/original.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --content NEW --line_number 3 ${B})
check "t1-rc" 0 $?
expect_output "t1-msg" "$out" "Inserted 1 line(s)"
expect_output "t1-where" "$out" "before line 3"
expect_file "t1-bytes" fixtures/work.txt fixtures/exp_insert3.txt

echo
echo "=== 2. Insert at beginning (line_number=1) ==="
cp fixtures/original.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --content TOP --line_number 1 ${B})
check "t2-rc" 0 $?
expect_output "t2-where" "$out" "at the beginning"
expect_file "t2-bytes" fixtures/work.txt fixtures/exp_insert_top.txt

echo
echo "=== 3. Insert at end (line_number=6 = n+1) ==="
cp fixtures/original.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --content END --line_number 6 ${B})
check "t3-rc" 0 $?
expect_output "t3-where" "$out" "at the end"
expect_file "t3-bytes" fixtures/work.txt fixtures/exp_insert_end.txt

echo
echo "=== 4. after_line=5 (equivalent to end) ==="
cp fixtures/original.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --content END --line_number 1 --after_line 5 --dry_run False)
check "t4-rc" 0 $?
expect_output "t4-where" "$out" "at the end"
expect_file "t4-bytes" fixtures/work.txt fixtures/exp_insert_end.txt

echo
echo "=== 5. after_line=0 == beginning ==="
cp fixtures/original.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --content ZERO --line_number 1 --after_line 0 --dry_run False)
check "t5-rc" 0 $?
expect_output "t5-where" "$out" "at the beginning"
head -1 fixtures/work.txt | grep -qF "ZERO" && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: ZERO not first"; }

echo
echo "=== 6. Multi-line content (line_number=3) ==="
cp fixtures/original.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --content $'A1\nA2\nA3' --line_number 3 ${B})
check "t6-rc" 0 $?
expect_output "t6-count" "$out" "Inserted 3 line(s)"
expect_file "t6-bytes" fixtures/work.txt fixtures/exp_multi.txt

echo
echo "=== 7. dry_run: file unmodified ==="
cp fixtures/original.txt fixtures/work.txt
md5b=$(md5 fixtures/work.txt)
out=$($H --path fixtures/work.txt --content GHOST --line_number 3 --after_line None --dry_run True)
check "t7-rc" 0 $?
expect_output "t7-dry" "$out" "DRY RUN"
unchanged "t7" "$md5b" "$(md5 fixtures/work.txt)"

echo
echo "=== 8. Empty file → insert gets trailing newline ==="
: > fixtures/work_empty.txt
out=$($H --path fixtures/work_empty.txt --content FIRST --line_number 1 ${B})
check "t8-rc" 0 $?
expect_output "t8-count" "$out" "Inserted 1 line(s)"
tail -c 1 fixtures/work_empty.txt | od -An -tx1 | grep -q "0a" && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: missing trailing newline"; }

echo
echo "=== 9. No trailing newline + insert at end → preserved ==="
printf 'a\nb' > fixtures/work_no_nl.txt
out=$($H --path fixtures/work_no_nl.txt --content NEW --line_number 3 ${B})
check "t9-rc" 0 $?
printf 'a\nb\nNEW' > fixtures/exp9_sr.txt
expect_file "t9-bytes" fixtures/work_no_nl.txt fixtures/exp9_sr.txt

echo
echo "=== 10. No trailing newline + insert at beginning → preserved ==="
printf 'a\nb' > fixtures/work_no_nl.txt
out=$($H --path fixtures/work_no_nl.txt --content MID --line_number 1 ${B})
check "t10-rc" 0 $?
printf 'MID\na\nb' > fixtures/exp10_sr.txt
expect_file "t10-bytes" fixtures/work_no_nl.txt fixtures/exp10_sr.txt

echo
echo "=== 11. Errors ==="
out=$($H --path /tmp/no_such_file_il --content X --line_number 1 ${B})
check "t11a-missing" 1 $?
expect_output "t11a-msg" "$out" "ERROR"

out=$($H --path /tmp --content X --line_number 1 ${B})
check "t11b-directory" 1 $?
expect_output "t11b-msg" "$out" "ERROR"

cp fixtures/original.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --content X --line_number 0 ${B})
check "t11c-linenum-0" 1 $?
expect_output "t11c-msg" "$out" "out of range"

out=$($H --path fixtures/work.txt --content X --line_number 7 ${B})
check "t11d-linenum-7" 1 $?
expect_output "t11d-msg" "$out" "out of range"

out=$($H --path fixtures/work.txt --content X --line_number 1 --after_line 6 --dry_run False)
check "t11e-after-too-big" 1 $?
expect_output "t11e-msg" "$out" "out of range"

out=$($H --path fixtures/work.txt --content X --line_number 1 --after_line -1 --dry_run False)
check "t11f-after-neg" 1 $?
expect_output "t11f-msg" "$out" "out of range"

out=$($H --path fixtures/work.txt --content "" --line_number 1 ${B})
check "t11g-empty-content" 1 $?
expect_output "t11g-msg" "$out" "empty"

out=$($H --path fixtures/work.txt --content X --line_number 2 --after_line 1 --dry_run False)
check "t11h-both" 1 $?
expect_output "t11h-msg" "$out" "mutually exclusive"

echo
echo "=== 12. Non-integer line_number ==="
cp fixtures/original.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --content X --line_number abc --after_line None --dry_run False)
check "t12-non-int" 1 $?
expect_output "t12-msg" "$out" "must be an integer"

echo
echo "=== 13. String digit accepted (lenient coercion) ==="
cp fixtures/original.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --content X --line_number 4 ${B})
check "t13-string-digit" 0 $?
sed -n '4p' fixtures/work.txt | grep -qF "X" && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: X not on line 4"; }

echo
echo "=== 14. dry_run output is a valid unified diff ==="
cp fixtures/original.txt fixtures/work.txt
out=$($H --path fixtures/work.txt --content $'A1\nA2' --line_number 3 --after_line None --dry_run True)
check "t14-rc" 0 $?
if echo "$out" | grep -q "^---"; then pass=$((pass+1)); else fail=$((fail+1)); echo "FAIL: no --- in diff"; fi
if echo "$out" | grep -q "^+++"; then pass=$((pass+1)); else fail=$((fail+1)); echo "FAIL: no +++ in diff"; fi
if echo "$out" | grep -q "^@@"; then pass=$((pass+1)); else fail=$((fail+1)); echo "FAIL: no @@ in diff"; fi

echo
echo "=== 15. dry_run marks a missing trailing newline (and only then) ==="
printf 'a\nb' > fixtures/work_no_nl.txt
out=$(il fixtures/work_no_nl.txt X 2 True)
check "t15a-rc" 0 $?
expect_output "t15a-marker" "$out" "\ No newline at end of file"
printf 'a\nb' > fixtures/work_no_nl.txt
out=$(il fixtures/work_no_nl.txt NEW 3 True)
check "t15b-rc" 0 $?
expect_output "t15b-marker" "$out" "\ No newline at end of file"
cp fixtures/original.txt fixtures/work.txt
out=$(il fixtures/work.txt X 3 False)
check "t15c-rc" 0 $?
echo "$out" | grep -qF "No newline" && { fail=$((fail+1)); echo "FAIL: marker on a file that ends with a newline"; } || pass=$((pass+1))
cp fixtures/original.txt fixtures/work.txt
out=$(il fixtures/work.txt X 3 True)
check "t15d-rc" 0 $?
echo "$out" | grep -qF "No newline" && { fail=$((fail+1)); echo "FAIL: marker on a file that ends with a newline"; } || pass=$((pass+1))

echo
echo "=== 16. dry_run diff is pasteable into the patch tool ==="
printf 'a\nb' > fixtures/il_nonl.txt
printf '\n\nalpha\n' > fixtures/il_blank.txt
: > fixtures/il_empty.txt
roundtrip fixtures/original.txt X 3 t16a-middle
roundtrip fixtures/original.txt TOP 1 t16b-beginning
roundtrip fixtures/original.txt END 6 t16c-end
roundtrip fixtures/il_nonl.txt X 2 t16d-nonl-middle
roundtrip fixtures/il_nonl.txt NEW 3 t16e-nonl-end
roundtrip fixtures/il_nonl.txt TOP 1 t16f-nonl-beginning
roundtrip fixtures/il_blank.txt MID 2 t16g-blank
roundtrip fixtures/il_empty.txt FIRST 1 t16h-empty-file
roundtrip fixtures/il_blank.txt $'A\nB' 1 t16i-multiline

echo
echo "=== 17. round-tripped result is byte-identical, not just line-identical ==="
printf 'a\nb' > fixtures/il_nonl.txt
roundtrip fixtures/il_nonl.txt X 2 t17-bytes-check > /dev/null
tail -c 1 $FIXTURES/il_rt.txt | od -An -tx1 | grep -q "62" && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: patched file gained a trailing newline"; }

echo
echo "=== 18. the inserted line takes the file's own line terminator ==="
cp fixtures/original_crlf.txt fixtures/work.txt
out=$(il fixtures/work.txt MID 2 False)
check "t18a-rc" 0 $?
expect_file "t18a-crlf-mid" fixtures/work.txt fixtures/exp_crlf_mid.txt
cp fixtures/original_crlf.txt fixtures/work.txt
il fixtures/work.txt END 4 False > /dev/null
expect_file "t18b-crlf-end" fixtures/work.txt fixtures/exp_crlf_end.txt
count=$(grep -c $'\r' fixtures/work.txt)
[ "$count" -eq 4 ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: CRLF count is $count, expected 4"; }
cp fixtures/original_crlf_nonl.txt fixtures/work.txt
il fixtures/work.txt NEW 3 False > /dev/null
expect_file "t18c-crlf-nonl-end" fixtures/work.txt fixtures/exp_crlf_nonl_end.txt
cp fixtures/original_cr.txt fixtures/work.txt
il fixtures/work.txt X 2 False > /dev/null
expect_file "t18d-lone-cr" fixtures/work.txt fixtures/exp_cr_mid.txt
cp fixtures/original_mixed.txt fixtures/work.txt
il fixtures/work.txt X 2 False > /dev/null
expect_file "t18e-mixed" fixtures/work.txt fixtures/exp_mixed_mid.txt
cp fixtures/original.txt fixtures/work.txt
il fixtures/work.txt NEW 3 False > /dev/null
expect_file "t18f-lf-unchanged" fixtures/work.txt fixtures/exp_insert3.txt
count=$(grep -c $'\r' fixtures/work.txt || true)
[ "$count" -eq 0 ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: LF file gained $count CR characters"; }

echo
echo "=== 19. insert_line and patch agree byte-for-byte on every terminator ==="
roundtrip fixtures/original_crlf.txt MID 2 t19a-crlf-mid
roundtrip fixtures/original_crlf.txt END 4 t19b-crlf-end
roundtrip fixtures/original_crlf.txt TOP 1 t19c-crlf-beginning
roundtrip fixtures/original_crlf_nonl.txt NEW 3 t19d-crlf-nonl-end
roundtrip fixtures/original_cr.txt X 2 t19e-lone-cr
roundtrip fixtures/original_mixed.txt X 2 t19f-mixed

summary
