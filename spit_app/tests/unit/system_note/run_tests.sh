#!/bin/bash
# Unit tests for the P13 system-note generator: spit_app/chat/system_note.py.
#
# NO VENV PREAMBLE - AND THAT ABSENCE IS THE GATE (TRAPS #19, inverted).
# The module under test imports NOTHING of the app's runtime, so this suite runs
# on the bare system python3, and every other interpreter choice would weaken
# it: spit_app/chat/ is a namespace package (no __init__.py), so `import
# spit_app.chat.system_note` pulls in no sibling module either. If a later edit
# gives the module a Textual or httpx import, the file dies HERE - t1 is the
# in-file check and the loop below is the loud reporting of it. Pointing
# quietly at ~/.venv-spit instead would let the suite keep passing while becoming
# venv-bound without ever saying so. (unit:endpoints is the suite that needs the
# venv, because the module IT tests imports httpx; this one must not, and on a
# machine without ~/.venv-spit it still measures everything.)
#
# A file that dies before printing its summary counts as ONE FAILURE and is
# named: a row of `PASS: 0  FAIL: 0` from a suite that never ran is
# indistinguishable from a green (the mistake 39ceb2f fixed for discarded
# failures), and the outer runner reads only `tail -n 1` (TRAPS #18) - so the
# row itself has to carry the failure.
cd "$(dirname $0)"
rc=0
out=""
for test in test_*.py; do
	this=$(python3 "./${test}")
	status=${?}
	echo "${this}"
	if printf '%s\n' "${this}" | grep -q '^PASS: '; then
		[ "${status}" -eq 0 ] || rc=1
	else
		echo "FAIL: ${test} died before reporting its checks (exit ${status}):"
		echo "      it measured nothing - read the traceback above."
		rc=1
		this="${this}"$'\n'"PASS: 0  FAIL: 1"
	fi
	out+="${this}"$'\n'
done
totals=$(printf '%s\n' "${out}" | grep -E '^PASS: ' | awk '{p+=$2; f+=$4} END {print p+0, f+0}')
pass=${totals% *}
fail=${totals#* }
echo
echo "=============================="
echo "PASS: ${pass}  FAIL: ${fail}"
[ "${fail}" -eq 0 ] && [ ${rc} -eq 0 ]
