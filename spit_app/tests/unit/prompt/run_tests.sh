#!/bin/bash
# Unit tests for the system prompt chat/work.py assembles for the model
# (pure Python, no Textual - stub_modules.py stands in for its imports).
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
