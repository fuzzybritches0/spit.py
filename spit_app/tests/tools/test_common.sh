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
