#!/bin/bash
# Build the test environment: one venv with everything in requirements.txt.
#
# Why this exists: the app's dependencies (libtmux, textual, ...) are NOT in the
# bare system python3 (TRAPS #19), and the unit suites that need them -- today
# unit:terminal, which drives a real tmux through libtmux -- cannot run without
# one. This script is the documented way to get it; doc/TESTING.md points here.
#
# The two unset lines are not decoration. This sandbox exports
# PIP_USER=True and PIP_BREAK_SYSTEM_PACKAGES=True so that installs work against
# the system interpreter, and a virtualenv refuses a --user install outright
# ("Can not perform a '--user' install. User site-packages are not visible in
# this virtualenv."), so without unsetting them the install fails on the first
# package and pip leaves you with an empty venv.

set -e

VENV="${SPIT_TEST_VENV:-${HOME}/.venv-spit}"
REPO="$(cd "$(dirname "${0}")/../.." && pwd)"

unset PIP_USER
unset PIP_BREAK_SYSTEM_PACKAGES

python3 -m venv "${VENV}"
"${VENV}/bin/python3" -m pip install --upgrade pip
"${VENV}/bin/python3" -m pip install -r "${REPO}/requirements.txt"

echo
echo "test venv ready at ${VENV}"
echo "suites that need dependencies pick it up on their own; to use another one:"
echo "  SPIT_TEST_PYTHON=/path/to/python bash spit_app/tests/run_tests.sh"
