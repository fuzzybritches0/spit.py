#!/bin/bash
# Unit tests for the terminal/lsterm tmux backend (pure Python, no Textual).
#
# These drive a REAL tmux through libtmux, so they need libtmux -- which the bare
# system python3 does not have (TRAPS #19). The interpreter is chosen the same way
# every time: SPIT_TEST_PYTHON if it is set, then the test venv doc/TESTING.md
# tells you to build, then whatever python3 is on PATH if it can import libtmux.
#
# Missing dependency is a FAILURE, never a quiet zero: a suite that reports
# `PASS: 0  FAIL: 0` when it could not start looks identical to a suite that ran
# and passed, which is the mistake 39ceb2f fixed for discarded failures. The row
# goes red and says what to build.
cd "$(dirname $0)"

PYTHON="${SPIT_TEST_PYTHON}"
if [ -z "${PYTHON}" ]; then
	for candidate in "${HOME}/.venv-spit/bin/python3" "$(command -v python3)"; do
		if [ -x "${candidate}" ] && "${candidate}" -c "import libtmux" >/dev/null 2>&1; then
			PYTHON="${candidate}"
			break
		fi
	done
fi

if [ -z "${PYTHON}" ] || ! command -v tmux >/dev/null 2>&1; then
	echo "FAIL: the terminal suite cannot start - it needs the tmux binary and libtmux."
	[ -z "${PYTHON}" ] && echo "  no python with libtmux: build the test venv (doc/TESTING.md) and run"
	[ -z "${PYTHON}" ] && echo "    bash spit_app/tests/create_venv.sh"
	[ -z "${PYTHON}" ] && echo "  or point SPIT_TEST_PYTHON at one that has it."
	! command -v tmux >/dev/null 2>&1 && echo "  tmux is not installed."
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
