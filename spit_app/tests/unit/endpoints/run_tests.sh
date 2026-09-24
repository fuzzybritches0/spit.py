#!/bin/bash
# The P12 endpoint suite: payload, stream parse, token counts, context sizes -
# driven against a canned stdlib HTTP server on 127.0.0.1, no live model.
#
# This is the FIFTH dependency-listed suite (TRAPS #19): the code under test,
# `endpoints/llamacpp.py`, imports **httpx**, which the bare system python3 does
# not have (measured on this box: `ModuleNotFoundError: No module named 'httpx'`),
# and the counts row (t11) drives `chat_settings`, which pulls **Textual**. So
# the probe is BOTH imports - one gate for both is honest, and one row for the
# suite is cheap.
#
# The interpreter is chosen the same way unit:terminal / unit:anchored /
# unit:chat_smoke / unit:chat_window do it (this preamble is theirs verbatim,
# with the probe widened): SPIT_TEST_PYTHON if set, then the test venv
# doc/TESTING.md tells you to build, then whatever python3 is on PATH if it can
# import the dependency.
#
# Missing dependency is a FAILURE, never a quiet zero: a suite that reports
# `PASS: 0  FAIL: 0` when it could not start looks identical to one that ran
# and passed (the mistake 39ceb2f fixed for discarded failures). The row goes
# red and says what to build.
cd "$(dirname $0)"

PYTHON="${SPIT_TEST_PYTHON}"
if [ -z "${PYTHON}" ]; then
	for candidate in "${HOME}/.venv-spit/bin/python3" "$(command -v python3)"; do
		if [ -x "${candidate}" ] && "${candidate}" -c "import httpx, textual" >/dev/null 2>&1; then
			PYTHON="${candidate}"
			break
		fi
	done
fi

if [ -z "${PYTHON}" ]; then
	echo "FAIL: the endpoints suite cannot start - it needs httpx (endpoints/llamacpp.py) and Textual (chat_settings, t11)."
	echo "  no python with httpx and textual: build the test venv (doc/TESTING.md) and run"
	echo "    bash spit_app/tests/create_venv.sh"
	echo "  or point SPIT_TEST_PYTHON at one that has both."
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
