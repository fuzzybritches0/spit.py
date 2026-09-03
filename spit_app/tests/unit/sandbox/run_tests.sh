#!/bin/bash
# Unit tests for the sandbox script wrapper and delivery (pure Python, no Textual).
cd "$(dirname $0)"
rc=0
out=""
for test in test_*.py; do
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
