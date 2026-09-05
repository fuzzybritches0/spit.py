#!/bin/bash
cd "$(dirname ${0})"
source ../test_common.sh
trap remove_fixtures EXIT
rm -rf ./fixtures
bash ./create_fixtures.sh || exit 1
FIXTURES=$PWD/fixtures
H="python3 ../harness.py"

# rn OLD NEW DRY - the complete argument set on every call (TRAPS #9)
rn() {
  $H --old_path "$1" --new_path "$2" --dry_run "$3"
}

# a dangling symlink exists too - existence is lexists() in the tool
exists() {
  if [ -e "$2" ] || [ -L "$2" ]; then
    pass=$((pass+1))
  else
    fail=$((fail+1)); echo "FAIL(exists): $1: $2"
  fi
}

gone() {
  if [ ! -e "$2" ] && [ ! -L "$2" ]; then
    pass=$((pass+1))
  else
    fail=$((fail+1)); echo "FAIL(gone): $1: $2"
  fi
}

echo "=== 1. Rename a file: bytes move, source gone ==="
out=$(rn fixtures/t01-source.txt fixtures/t01-target.txt False)
check "t1-rc" 0 $?
expect_output "t1-msg" "$out" "Renamed file"
expect_file "t1-bytes" fixtures/t01-target.txt fixtures/t01-exp-target.txt
gone "t1-source-gone" fixtures/t01-source.txt

echo
echo "=== 2. Line endings and the final byte are untouched ==="
before=$(md5 fixtures/t02-source-crlf.txt)
out=$(rn fixtures/t02-source-crlf.txt fixtures/t02-moved.txt False)
check "t2-rc" 0 $?
unchanged "t2-md5" "$before" "$(md5 fixtures/t02-moved.txt)"
assert_cr_lines "t2-crlf" fixtures/t02-moved.txt 3
assert_last_byte "t2-last" fixtures/t02-moved.txt 0a
gone "t2-source-gone" fixtures/t02-source-crlf.txt

echo
echo "=== 3. A directory moves with its whole tree ==="
out=$(rn fixtures/t03-src-dir fixtures/t03-moved-dir False)
check "t3-rc" 0 $?
expect_output "t3-msg" "$out" "Renamed directory"
expect_file "t3-inner" fixtures/t03-moved-dir/inner.txt fixtures/t03-exp-inner.txt
expect_file "t3-deeper" fixtures/t03-moved-dir/deep/deeper.txt fixtures/t03-exp-deeper.txt
gone "t3-old-gone" fixtures/t03-src-dir

echo
echo "=== 4. dry_run: identical report, nothing moves ==="
before=$(md5 fixtures/t04-source.txt)
out=$(rn fixtures/t04-source.txt fixtures/t04-target.txt True)
check "t4-rc" 0 $?
expect_output "t4-dry" "$out" "DRY RUN"
expect_output "t4-would" "$out" "Would rename file"
unchanged "t4-source-untouched" "$before" "$(md5 fixtures/t04-source.txt)"
gone "t4-target-not-created" fixtures/t04-target.txt

echo
echo "=== 5. An existing target is refused, both files untouched ==="
md5_a=$(md5 fixtures/t05-a.txt); md5_b=$(md5 fixtures/t05-b.txt)
out=$(rn fixtures/t05-a.txt fixtures/t05-b.txt False)
check "t5-rc" 1 $?
expect_output "t5-refusal" "$out" "rename never overwrites"
unchanged "t5-source-untouched" "$md5_a" "$(md5 fixtures/t05-a.txt)"
unchanged "t5-target-untouched" "$md5_b" "$(md5 fixtures/t05-b.txt)"

echo
echo "=== 6. A dangling symlink counts as an existing target ==="
ln -s ./t06-nonexistent fixtures/t06-dangling
before=$(md5 fixtures/t06-source.txt)
out=$(rn fixtures/t06-source.txt fixtures/t06-dangling False)
check "t6-rc" 1 $?
expect_output "t6-refusal" "$out" "rename never overwrites"
unchanged "t6-source-untouched" "$before" "$(md5 fixtures/t06-source.txt)"

echo
echo "=== 7. A missing source is named ==="
out=$(rn fixtures/t07-no-such-file fixtures/t07-new.txt False)
check "t7-rc" 1 $?
expect_output "t7-msg" "$out" "does not exist"
gone "t7-no-target" fixtures/t07-new.txt

echo
echo "=== 8. A missing target parent is named, source intact ==="
out=$(rn fixtures/t08-source.txt fixtures/t08-no-such-dir/x.txt False)
check "t8-rc" 1 $?
expect_output "t8-msg" "$out" "Target directory does not exist"
exists "t8-source-intact" fixtures/t08-source.txt

echo
echo "=== 9. The same path is refused ==="
out=$(rn fixtures/t09-source.txt fixtures/t09-source.txt False)
check "t9-rc" 1 $?
expect_output "t9-msg" "$out" "same path"
exists "t9-source-intact" fixtures/t09-source.txt

echo
echo "=== 10. The same path spelled differently is refused too ==="
out=$(rn fixtures/t10-source.txt fixtures/./t10-source.txt False)
check "t10-rc" 1 $?
expect_output "t10-msg" "$out" "same path"
exists "t10-source-intact" fixtures/t10-source.txt

echo
echo "=== 11. An empty new_path is refused ==="
before=$(md5 fixtures/t04-source.txt)
out=$(rn fixtures/t04-source.txt "" False)
check "t11-rc" 1 $?
expect_output "t11-msg" "$out" "both required and must not be empty"
unchanged "t11-source-untouched" "$before" "$(md5 fixtures/t04-source.txt)"

echo
echo "=== 12. Spaces in both paths work ==="
out=$(rn "fixtures/t12 src file.txt" "fixtures/t12 dst file.txt" False)
check "t12-rc" 0 $?
expect_output "t12-msg" "$out" "Renamed file"
expect_file "t12-bytes" "fixtures/t12 dst file.txt" fixtures/t12-exp.txt
gone "t12-source-gone" "fixtures/t12 src file.txt"

echo
echo "=== 13. dry_run refuses what the real call would refuse ==="
md5_a=$(md5 fixtures/t13-a.txt); md5_b=$(md5 fixtures/t13-b.txt)
out=$(rn fixtures/t13-a.txt fixtures/t13-b.txt True)
check "t13-rc" 1 $?
expect_output "t13-refusal" "$out" "rename never overwrites"
unchanged "t13-source-untouched" "$md5_a" "$(md5 fixtures/t13-a.txt)"
unchanged "t13-target-untouched" "$md5_b" "$(md5 fixtures/t13-b.txt)"

echo
echo "=== 14. A directory cannot move into its own subtree ==="
out=$(rn fixtures/t14-src-dir fixtures/t14-src-dir/subdir/moved False)
check "t14-rc" 1 $?
expect_output "t14-msg" "$out" "into itself"
exists "t14-tree-intact" fixtures/t14-src-dir/subdir/keep.txt

echo
echo "=== 15. An existing target directory is refused ==="
out=$(rn fixtures/t15-source.txt fixtures/t15-target-dir False)
check "t15-rc" 1 $?
expect_output "t15-refusal" "$out" "rename never overwrites"
exists "t15-source-intact" fixtures/t15-source.txt
exists "t15-dir-intact" fixtures/t15-target-dir/inside.txt

echo
echo "=== 16. A symlink moves as a symlink (link, not pointee) ==="
ln -s ./t16-pointee fixtures/t16-link
out=$(rn fixtures/t16-link fixtures/t16-link-moved False)
check "t16-rc" 0 $?
expect_output "t16-msg" "$out" "Renamed symlink"
if [ "$(readlink fixtures/t16-link-moved)" == "./t16-pointee" ]; then
  pass=$((pass+1))
else
  fail=$((fail+1)); echo "FAIL: t16-pointing: $(readlink fixtures/t16-link-moved)"
fi
gone "t16-old-gone" fixtures/t16-link
gone "t16-pointee-still-absent" fixtures/t16-pointee

echo
echo "=== 17. Binary bytes (NULs, high bytes) survive the move ==="
before=$(md5 fixtures/t17-binary.bin)
out=$(rn fixtures/t17-binary.bin fixtures/t17-moved.bin False)
check "t17-rc" 0 $?
unchanged "t17-md5" "$before" "$(md5 fixtures/t17-moved.bin)"
assert_last_byte "t17-last" fixtures/t17-moved.bin ff
gone "t17-source-gone" fixtures/t17-binary.bin

echo
echo "=== 18. An empty old_path is refused ==="
out=$(rn "" fixtures/t18-new.txt False)
check "t18-rc" 1 $?
expect_output "t18-msg" "$out" "both required and must not be empty"
gone "t18-no-target" fixtures/t18-new.txt

summary
