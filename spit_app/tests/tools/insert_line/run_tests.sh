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
  cp "$src" fixtures/shared-rt-work.txt
  cp "$src" $FIXTURES/shared-rt-src.txt
  il $FIXTURES/shared-rt-src.txt "$content" "$line" True | extract_diff > $FIXTURES/shared-rt.diff
  [ -s $FIXTURES/shared-rt.diff ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: $label empty diff"; }
  il fixtures/shared-rt-work.txt "$content" "$line" False > /dev/null
  ( cd "$patch_dir" && python3 ../harness.py --path $FIXTURES/shared-rt-src.txt \
    --diff "$(cat $FIXTURES/shared-rt.diff)" --reverse False --dry_run False ) > /dev/null
  check "$label-patch-rc" 0 $?
  expect_file "$label" $FIXTURES/shared-rt-src.txt fixtures/shared-rt-work.txt
}


echo "=== 1. Insert in the middle (line_number=3) ==="
cp fixtures/shared-original.txt fixtures/t01-work.txt
out=$($H --path fixtures/t01-work.txt --content NEW --line_number 3 ${B})
check "t1-rc" 0 $?
expect_output "t1-msg" "$out" "Inserted 1 line(s)"
expect_output "t1-where" "$out" "before line 3"
expect_file "t1-bytes" fixtures/t01-work.txt fixtures/shared-exp-insert3.txt

echo
echo "=== 2. Insert at beginning (line_number=1) ==="
cp fixtures/shared-original.txt fixtures/t02-work.txt
out=$($H --path fixtures/t02-work.txt --content TOP --line_number 1 ${B})
check "t2-rc" 0 $?
expect_output "t2-where" "$out" "at the beginning"
expect_file "t2-bytes" fixtures/t02-work.txt fixtures/t02-exp-insert-top.txt

echo
echo "=== 3. Insert at end (line_number=6 = n+1) ==="
cp fixtures/shared-original.txt fixtures/t03-work.txt
out=$($H --path fixtures/t03-work.txt --content END --line_number 6 ${B})
check "t3-rc" 0 $?
expect_output "t3-where" "$out" "at the end"
expect_file "t3-bytes" fixtures/t03-work.txt fixtures/shared-exp-insert-end.txt

echo
echo "=== 4. after_line=5 (equivalent to end) ==="
cp fixtures/shared-original.txt fixtures/t04-work.txt
out=$($H --path fixtures/t04-work.txt --content END --line_number 1 --after_line 5 --dry_run False)
check "t4-rc" 0 $?
expect_output "t4-where" "$out" "at the end"
expect_file "t4-bytes" fixtures/t04-work.txt fixtures/shared-exp-insert-end.txt

echo
echo "=== 5. after_line=0 == beginning ==="
cp fixtures/shared-original.txt fixtures/t05-work.txt
out=$($H --path fixtures/t05-work.txt --content ZERO --line_number 1 --after_line 0 --dry_run False)
check "t5-rc" 0 $?
expect_output "t5-where" "$out" "at the beginning"
head -1 fixtures/t05-work.txt | grep -qF "ZERO" && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: ZERO not first"; }

echo
echo "=== 6. Multi-line content (line_number=3) ==="
cp fixtures/shared-original.txt fixtures/t06-work.txt
out=$($H --path fixtures/t06-work.txt --content $'A1\nA2\nA3' --line_number 3 ${B})
check "t6-rc" 0 $?
expect_output "t6-count" "$out" "Inserted 3 line(s)"
expect_file "t6-bytes" fixtures/t06-work.txt fixtures/t06-exp-multi.txt

echo
echo "=== 7. dry_run: file unmodified ==="
cp fixtures/shared-original.txt fixtures/t07-work.txt
md5b=$(md5 fixtures/t07-work.txt)
out=$($H --path fixtures/t07-work.txt --content GHOST --line_number 3 --after_line None --dry_run True)
check "t7-rc" 0 $?
expect_output "t7-dry" "$out" "DRY RUN"
unchanged "t7" "$md5b" "$(md5 fixtures/t07-work.txt)"

echo
echo "=== 8. Empty file → insert gets trailing newline ==="
: > fixtures/t08-work-empty.txt
out=$($H --path fixtures/t08-work-empty.txt --content FIRST --line_number 1 ${B})
check "t8-rc" 0 $?
expect_output "t8-count" "$out" "Inserted 1 line(s)"
tail -c 1 fixtures/t08-work-empty.txt | od -An -tx1 | grep -q "0a" && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: missing trailing newline"; }

echo
echo "=== 9. No trailing newline + insert at end → preserved ==="
printf 'a\nb' > fixtures/t09-work-no-nl.txt
out=$($H --path fixtures/t09-work-no-nl.txt --content NEW --line_number 3 ${B})
check "t9-rc" 0 $?
printf 'a\nb\nNEW' > fixtures/t09-exp.txt
expect_file "t9-bytes" fixtures/t09-work-no-nl.txt fixtures/t09-exp.txt

echo
echo "=== 10. No trailing newline + insert at beginning → preserved ==="
printf 'a\nb' > fixtures/t10-work-no-nl.txt
out=$($H --path fixtures/t10-work-no-nl.txt --content MID --line_number 1 ${B})
check "t10-rc" 0 $?
printf 'MID\na\nb' > fixtures/t10-exp.txt
expect_file "t10-bytes" fixtures/t10-work-no-nl.txt fixtures/t10-exp.txt

echo
echo "=== 11. Errors ==="
out=$($H --path fixtures/t11-no-such-file --content X --line_number 1 ${B})
check "t11a-missing" 1 $?
expect_output "t11a-msg" "$out" "ERROR"

out=$($H --path fixtures --content X --line_number 1 ${B})
check "t11b-directory" 1 $?
expect_output "t11b-msg" "$out" "ERROR"

cp fixtures/shared-original.txt fixtures/t11-work.txt
out=$($H --path fixtures/t11-work.txt --content X --line_number 0 ${B})
check "t11c-linenum-0" 1 $?
expect_output "t11c-msg" "$out" "out of range"

out=$($H --path fixtures/t11-work.txt --content X --line_number 7 ${B})
check "t11d-linenum-7" 1 $?
expect_output "t11d-msg" "$out" "out of range"

out=$($H --path fixtures/t11-work.txt --content X --line_number 1 --after_line 6 --dry_run False)
check "t11e-after-too-big" 1 $?
expect_output "t11e-msg" "$out" "out of range"

out=$($H --path fixtures/t11-work.txt --content X --line_number 1 --after_line -1 --dry_run False)
check "t11f-after-neg" 1 $?
expect_output "t11f-msg" "$out" "out of range"

out=$($H --path fixtures/t11-work.txt --content "" --line_number 1 ${B})
check "t11g-empty-content" 1 $?
expect_output "t11g-msg" "$out" "empty"

out=$($H --path fixtures/t11-work.txt --content X --line_number 2 --after_line 1 --dry_run False)
check "t11h-both" 1 $?
expect_output "t11h-msg" "$out" "mutually exclusive"

echo
echo "=== 12. Non-integer line_number ==="
cp fixtures/shared-original.txt fixtures/t12-work.txt
out=$($H --path fixtures/t12-work.txt --content X --line_number abc --after_line None --dry_run False)
check "t12-non-int" 1 $?
expect_output "t12-msg" "$out" "must be an integer"

echo
echo "=== 13. String digit accepted (lenient coercion) ==="
cp fixtures/shared-original.txt fixtures/t13-work.txt
out=$($H --path fixtures/t13-work.txt --content X --line_number 4 ${B})
check "t13-string-digit" 0 $?
sed -n '4p' fixtures/t13-work.txt | grep -qF "X" && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: X not on line 4"; }

echo
echo "=== 14. dry_run output is a valid unified diff ==="
cp fixtures/shared-original.txt fixtures/t14-work.txt
out=$($H --path fixtures/t14-work.txt --content $'A1\nA2' --line_number 3 --after_line None --dry_run True)
check "t14-rc" 0 $?
if echo "$out" | grep -q "^---"; then pass=$((pass+1)); else fail=$((fail+1)); echo "FAIL: no --- in diff"; fi
if echo "$out" | grep -q "^+++"; then pass=$((pass+1)); else fail=$((fail+1)); echo "FAIL: no +++ in diff"; fi
if echo "$out" | grep -q "^@@"; then pass=$((pass+1)); else fail=$((fail+1)); echo "FAIL: no @@ in diff"; fi

echo
echo "=== 15. dry_run marks a missing trailing newline (and only then) ==="
printf 'a\nb' > fixtures/t15-work-no-nl.txt
out=$(il fixtures/t15-work-no-nl.txt X 2 True)
check "t15a-rc" 0 $?
expect_output "t15a-marker" "$out" "\ No newline at end of file"
printf 'a\nb' > fixtures/t15-work-no-nl.txt
out=$(il fixtures/t15-work-no-nl.txt NEW 3 True)
check "t15b-rc" 0 $?
expect_output "t15b-marker" "$out" "\ No newline at end of file"
cp fixtures/shared-original.txt fixtures/t15-work.txt
out=$(il fixtures/t15-work.txt X 3 False)
check "t15c-rc" 0 $?
echo "$out" | grep -qF "No newline" && { fail=$((fail+1)); echo "FAIL: marker on a file that ends with a newline"; } || pass=$((pass+1))
cp fixtures/shared-original.txt fixtures/t15-work.txt
out=$(il fixtures/t15-work.txt X 3 True)
check "t15d-rc" 0 $?
echo "$out" | grep -qF "No newline" && { fail=$((fail+1)); echo "FAIL: marker on a file that ends with a newline"; } || pass=$((pass+1))

echo
echo "=== 16. dry_run diff is pasteable into the patch tool ==="
printf 'a\nb' > fixtures/t16-nonl.txt
printf '\n\nalpha\n' > fixtures/t16-blank.txt
: > fixtures/t16-empty.txt
roundtrip fixtures/shared-original.txt X 3 t16a-middle
roundtrip fixtures/shared-original.txt TOP 1 t16b-beginning
roundtrip fixtures/shared-original.txt END 6 t16c-end
roundtrip fixtures/t16-nonl.txt X 2 t16d-nonl-middle
roundtrip fixtures/t16-nonl.txt NEW 3 t16e-nonl-end
roundtrip fixtures/t16-nonl.txt TOP 1 t16f-nonl-beginning
roundtrip fixtures/t16-blank.txt MID 2 t16g-blank
roundtrip fixtures/t16-empty.txt FIRST 1 t16h-empty-file
roundtrip fixtures/t16-blank.txt $'A\nB' 1 t16i-multiline

echo
echo "=== 17. round-tripped result is byte-identical, not just line-identical ==="
printf 'a\nb' > fixtures/t17-nonl.txt
roundtrip fixtures/t17-nonl.txt X 2 t17-bytes-check > /dev/null
tail -c 1 $FIXTURES/shared-rt-src.txt | od -An -tx1 | grep -q "62" && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: patched file gained a trailing newline"; }

echo
echo "=== 18. the inserted line takes the file's own line terminator ==="
cp fixtures/shared-original-crlf.txt fixtures/t18-work.txt
out=$(il fixtures/t18-work.txt MID 2 False)
check "t18a-rc" 0 $?
expect_file "t18a-crlf-mid" fixtures/t18-work.txt fixtures/t18-exp-crlf-mid.txt
cp fixtures/shared-original-crlf.txt fixtures/t18-work.txt
il fixtures/t18-work.txt END 4 False > /dev/null
expect_file "t18b-crlf-end" fixtures/t18-work.txt fixtures/t18-exp-crlf-end.txt
count=$(grep -c $'\r' fixtures/t18-work.txt)
[ "$count" -eq 4 ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: CRLF count is $count, expected 4"; }
cp fixtures/shared-original-crlf-nonl.txt fixtures/t18-work.txt
il fixtures/t18-work.txt NEW 3 False > /dev/null
expect_file "t18c-crlf-nonl-end" fixtures/t18-work.txt fixtures/t18-exp-crlf-nonl-end.txt
cp fixtures/shared-original-cr.txt fixtures/t18-work.txt
il fixtures/t18-work.txt X 2 False > /dev/null
expect_file "t18d-lone-cr" fixtures/t18-work.txt fixtures/t18-exp-cr-mid.txt
cp fixtures/shared-original-mixed.txt fixtures/t18-work.txt
il fixtures/t18-work.txt X 2 False > /dev/null
expect_file "t18e-mixed" fixtures/t18-work.txt fixtures/t18-exp-mixed-mid.txt
cp fixtures/shared-original.txt fixtures/t18-work.txt
il fixtures/t18-work.txt NEW 3 False > /dev/null
expect_file "t18f-lf-unchanged" fixtures/t18-work.txt fixtures/shared-exp-insert3.txt
count=$(grep -c $'\r' fixtures/t18-work.txt || true)
[ "$count" -eq 0 ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "FAIL: LF file gained $count CR characters"; }

echo
echo "=== 19. insert_line and patch agree byte-for-byte on every terminator ==="
roundtrip fixtures/shared-original-crlf.txt MID 2 t19a-crlf-mid
roundtrip fixtures/shared-original-crlf.txt END 4 t19b-crlf-end
roundtrip fixtures/shared-original-crlf.txt TOP 1 t19c-crlf-beginning
roundtrip fixtures/shared-original-crlf-nonl.txt NEW 3 t19d-crlf-nonl-end
roundtrip fixtures/shared-original-cr.txt X 2 t19e-lone-cr
roundtrip fixtures/shared-original-mixed.txt X 2 t19f-mixed

summary
