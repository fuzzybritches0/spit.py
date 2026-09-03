#!/bin/bash
# Unit tests for the argument plumbing (pure Python, no Textual needed).
# The summaries of every test file are added up so the caller's `tail -n 1`
# sees one honest total.
cd "$(dirname $0)"
rc=0
out=""
for test in test_arguments.py test_pipeline.py; do
	this=$(python3 "./${test}") || rc=1
	echo "${this}"
	out+="${this}"$'\n'
done
totals=$(printf '%s\n' "${out}" | grep -E '^PASS: ' | awk '{p+=$2; f+=$4} END {print p+0, f+0}')
pass=${totals% *}
fail=${totals#* }
echo
echo "=============================="
echo "PASS: ${pass}  FAIL: ${fail}"
[ "${fail}" -eq 0 ] && [ ${rc} -eq 0 ]
