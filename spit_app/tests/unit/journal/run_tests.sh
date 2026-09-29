#!/bin/bash
# Unit tests for the P19/WP-3 journal tool: spit_app/tools/journal.py.
#
# NO VENV PREAMBLE - AND THAT ABSENCE IS THE GATE (TRAPS #19, inverted, the
# `unit:system_note` precedent). Measured on this box: loading `journal.py` on
# the bare system python3 puts NO `textual`, `httpx`, `libtmux`, `ddgs` or
# `playwright` in sys.modules - the module imports `os`, `time`, `pathlib` and
# `spit_app.tool_call.load_user_settings`, and `tool_call` imports only
# `spit_app.arguments` besides the stdlib. So the suite runs everywhere, and t1
# is the in-file check that it stays that way: give the tool a Textual import
# later and THIS reddens instead of the row quietly becoming venv-bound.
# (The suite that needs the venv is `unit:handoff`, whose code under test
# reaches the whole tool tree through `ToolCall`; this one does not.)
#
# A file that dies before printing its summary counts as ONE FAILURE and is
# named - the outer runner reads only `tail -n 1` (TRAPS #18), so a silent
# `PASS: 0  FAIL: 0` is the failure mode this runner refuses to print.
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
