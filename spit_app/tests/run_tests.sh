#!/bin/bash

cd "$(dirname ${0})"

for tool in tools/*; do
	if [ -d "${tool}" ] && [ -f "${tool}/run_tests.sh" ]; then
		echo -n "$(basename ${tool}): "
		"${tool}/run_tests.sh" | tail -n 1
	fi
done

for suite in unit/*; do
	if [ -d "${suite}" ] && [ -f "${suite}/run_tests.sh" ]; then
		echo -n "unit:$(basename ${suite}): "
		"${suite}/run_tests.sh" | tail -n 1
	fi
done
