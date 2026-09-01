#!/bin/bash
# fixtures_common.sh — test fixture creation for the tool test suites.
# Usage: sourced by each tool's create_fixtures.sh, which run_tests.sh executes.
#
# Nothing byte-sensitive is stored in the repository: every fixture is written at
# run time and removed afterwards, so no transport (git am, a checkout with
# core.autocrlf, an editor) can rewrite the line endings a test depends on.
#
# Functions:
#   testfile  PATH CONTENT      write CONTENT to PATH, creating parent directories
#   testfile_bytes PATH FORMAT  same, but FORMAT is a raw printf format string
#   fixtures_selftest           verify the generator itself, called by create_fixtures.sh
#
# CONTENT goes through printf '%b': \n \r \t and \0nnn (octal) are expanded, so
# 'a\nb' has no trailing newline and 'a\r\nb\r\n' is a CRLF file. Anything else
# that is not a known escape is written as-is; a literal backslash must be
# doubled ('\\n'), and note that '\c' would stop printf's output.

testfile() {
  mkdir -p "$(dirname "$1")"
  printf '%b' "$2" > "$1"
}

testfile_bytes() {
  mkdir -p "$(dirname "$1")"
  printf -- "$2" > "$1"
}

fixtures_selftest() {
  testfile ./fixtures/.selftest 'a\r\nb'
  local cr_lines
  cr_lines=$(grep -c $'\r' ./fixtures/.selftest || true)
  rm -f ./fixtures/.selftest
  if [ "$cr_lines" != "1" ]; then
    echo "FAIL: fixture generator is broken: the CRLF probe has $cr_lines CR line(s), expected 1"
    return 1
  fi
}
