#!/bin/bash

[ -f ~/.sandbox_env ] && source ~/.sandbox_env > /dev/null 2>&1
cat | "${@}"
