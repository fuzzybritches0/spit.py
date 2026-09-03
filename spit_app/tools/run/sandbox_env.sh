#!/bin/bash
# State left by the previous run_command call: the exported environment and the
# working directory. TRAILER in tools/run/run.py writes both; see STATE_EXCLUDE
# for what is deliberately not carried over.
#
# Only "export " lines are ours and only those are sourced. A state file written
# by an older version was a full `declare` dump, and replaying it errored on the
# read-only bash internals inside it -- BASHOPTS, BASH_VERSINFO, EUID. Those
# errors used to be swallowed by "> /dev/null 2>&1", which swallowed every real
# one with them, so they are shown now.

STATE="${HOME}/.sandbox_env"
CWD="${HOME}/.sandbox_cwd"

if [ -f "$STATE" ]; then
	source <(grep '^export ' "$STATE")
fi

# A directory that has gone away is not worth stopping for: the call starts in
# the sandbox home, which is what happened before there was any such state.
if [ -f "$CWD" ]; then
	DIR="$(cat "$CWD")"
	[ -d "$DIR" ] && cd -- "$DIR"
fi

"${@}" < /dev/stdin
