#!/bin/bash
# The P19/WP-4 recovery suite: the failure recovery, driven with the real Chat,
# the real SidePanel, the real Work and the real ToolCall over a canned stdlib
# HTTP server on 127.0.0.1 - no live model, no user data dir.
#
# This is a DEPENDENCY-LISTED suite (TRAPS #19) and its gate is copied from
# `unit:handoff` verbatim for a reason: it is the gate on what the code UNDER
# TEST imports, not on what these files happen to import. `chat/recovery.py`
# imports `Chat` (textual) and `endpoints/llamacpp` (httpx); the harness drives
# `ToolCall` - the tool tree the recovery deliberately bypasses, mounted so the
# world around it is the app's - and that tree imports httpx
# (get_current_weather),
# libtmux (terminal/lsterm), ddgs (websearch) and playwright (read_url). A
# missing one of those is a FAIL with the remedy, never a silent zero.
#
# The interpreter is chosen the same way unit:endpoints / unit:chat_smoke do
# it: SPIT_TEST_PYTHON if set, then the test venv doc/TESTING.md tells you to
# build, then whatever python3 is on PATH if it can import the lot.
cd "$(dirname $0)"

PYTHON="${SPIT_TEST_PYTHON}"
if [ -z "${PYTHON}" ]; then
	for candidate in "${HOME}/.venv-spit/bin/python3" "$(command -v python3)"; do
		if [ -x "${candidate}" ] && "${candidate}" -c "import textual, httpx, libtmux, ddgs, playwright" >/dev/null 2>&1; then
			PYTHON="${candidate}"
			break
		fi
	done
fi

if [ -z "${PYTHON}" ]; then
	echo "FAIL: the recovery suite cannot start - it drives ToolCall, which loads the whole tool tree (textual, httpx, libtmux, ddgs, playwright)."
	echo "  no python with all of them: build the test venv (doc/TESTING.md) and run"
	echo "    bash spit_app/tests/create_venv.sh"
	echo "  or point SPIT_TEST_PYTHON at one that has them."
	echo
	echo "=============================="
	echo "PASS: 0  FAIL: 1"
	exit 1
fi

rc=0
out=""
for test in test_*.py; do
	this=$("${PYTHON}" "./${test}") || rc=1
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
