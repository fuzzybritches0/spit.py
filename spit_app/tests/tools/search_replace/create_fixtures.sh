#!/bin/bash
source "$(dirname "${BASH_SOURCE[0]}")/../fixtures_common.sh"

fixtures_selftest || exit 1

testfile ./fixtures/t01-basic.txt 'This is old_word text with old_word in it.\nHere is old_word again.\n'
testfile ./fixtures/t02-regex.txt 'Numbers 123 and 456 and 789 should be replaced.\nAlso 1000 and 2000 are digit sequences.\n'
testfile ./fixtures/t03-multiple.txt 'First repeated second repeated third repeated fourth repeated fifth repeated\n'
testfile ./fixtures/t04-no-match.txt 'This file has no matches for the search string.\nNothing here will be replaced.\n'
testfile ./fixtures/shared-dry-run.txt 'This is unreplaced because this unreplaced text is unreplaced.\n'
testfile ./fixtures/t07-complex-regex.txt 'Hello World and Python Code are capitalized words here.\nthese words are all lowercase in this line.\n'
testfile ./fixtures/t08-multiline.txt 'line1\nline2\nline3\n'
