#!/bin/bash
# test_common.sh — shared test functions for tool test suites.
# Usage: source ../test_common.sh
#
# Functions:
#   check           NAME EXPECTED_RC ACTUAL_RC
#   expect_file     NAME GOT_FILE EXPECTED_FILE
#   expect_output   NAME OUTPUT EXPECTED_SUBSTRING
#   count_occurrences FILE NEEDLE        (outputs count to stdout)
#   md5             FILE                 (outputs md5 to stdout)
#   unchanged       NAME OLD_MD5 NEW_MD5
#   assert_cr_lines NAME FILE COUNT      (lines containing CR, generator-independent)
#   assert_no_cr    NAME FILE
#   assert_last_byte NAME FILE HEX       ('0a' = ends with a newline)
#   remove_fixtures                      delete ./fixtures unless KEEP_FIXTURES=1
#   summary                            (prints PASS/FAIL, exits with status)

pass=0; fail=0

check() {
  if [ "$2" -eq "$3" ]; then
    pass=$((pass+1))
  else
    fail=$((fail+1))
    echo "FAIL(rc): $1 (expected $2, got $3)"
  fi
}

expect_file() {
  if cmp -s "$2" "$3"; then
    pass=$((pass+1))
  else
    fail=$((fail+1))
    echo "FAIL(file): $1: $2 != $3"
    echo "--- got ---"
    cat "$2"
    echo "--- expected ---"
    cat "$3"
  fi
}

expect_output() {
  if echo "$2" | grep -qF -- "$3"; then
    pass=$((pass+1))
  else
    fail=$((fail+1))
    echo "FAIL(output): $1"
    echo "  got: $2"
    echo "  expected to contain: $3"
  fi
}

count_occurrences() {
  grep -oF "$2" "$1" | wc -l
}

md5() {
  md5sum "$1" | cut -d' ' -f1
}

unchanged() {
  [ "$2" == "$3" ] && pass=$((pass+1)) || { fail=$((fail+1))
    echo "FAIL(md5): $1: file modified"; }
}

summary() {
  echo
  echo "=============================="
  echo "PASS: $pass  FAIL: $fail"
  [ $fail -eq 0 ]
}

assert_cr_lines() {
  local cr_lines
  cr_lines=$(grep -c $'\r' "$2" || true)
  if [ "$cr_lines" == "$3" ]; then
    pass=$((pass+1))
  else
    fail=$((fail+1))
    echo "FAIL(cr): $1: $2 has $cr_lines CR line(s), expected $3"
  fi
}

assert_no_cr() {
  assert_cr_lines "$1" "$2" 0
}

assert_last_byte() {
  local last_byte
  last_byte=$(tail -c 1 "$2" | od -An -tx1 | tr -d ' \n')
  if [ "$last_byte" == "$3" ]; then
    pass=$((pass+1))
  else
    fail=$((fail+1))
    echo "FAIL(last-byte): $1: $2 ends with '$last_byte', expected '$3'"
  fi
}

remove_fixtures() {
  [ -n "$KEEP_FIXTURES" ] || rm -rf ./fixtures
}
