#!/usr/bin/env bash
# HALO-128: automated test for hello_world.sh. Bash 3.2 compatible, no framework.
# Usage: bash test_hello_world.sh
# Exits 0 with "OK: <n> checks passed", or 1 naming every failing check.

DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SCRIPT="$DIR/hello_world.sh"

TMP=$(mktemp -d "${TMPDIR:-/tmp}/test_hello_world.XXXXXX") || {
  echo "FAIL: could not create a temp directory"; exit 1; }
trap 'rm -rf "$TMP"' EXIT

EXPECTED="$TMP/expected"
printf 'Hello, World!\n' > "$EXPECTED"

# Bash for the empty-environment case: the system /bin/bash when present.
if [ -x /bin/bash ]; then CLEAN_BASH=/bin/bash; else CLEAN_BASH=$BASH; fi

passed=0
failed=0
failures=""

check() { # check NAME CONDITION-RESULT(0 = pass)
  if [ "$2" -eq 0 ]; then
    passed=$((passed + 1))
  else
    failed=$((failed + 1))
    failures="$failures  FAIL: $1
"
  fi
}

# run_case NAME COMMAND...: run the command, then check stdout bytes, stderr, exit code.
run_case() {
  name=$1; shift
  ( cd "$DIR" && "$@" ) > "$TMP/out" 2> "$TMP/err"
  code=$?
  cmp -s "$EXPECTED" "$TMP/out"; check "$name: stdout is exactly 'Hello, World!\\n'" $?
  [ ! -s "$TMP/err" ]; check "$name: stderr is empty" $?
  [ "$code" -eq 0 ]; check "$name: exit code is 0 (got $code)" $?
}

run_case "bash hello_world.sh" bash "$SCRIPT"
run_case "bash hello_world.sh foo bar" bash "$SCRIPT" foo bar
run_case "env -i $CLEAN_BASH --noprofile --norc hello_world.sh" \
  env -i "$CLEAN_BASH" --noprofile --norc "$SCRIPT"
[ -x "$SCRIPT" ]; check "hello_world.sh has the executable bit" $?
run_case "./hello_world.sh" ./hello_world.sh

if [ "$failed" -eq 0 ]; then
  echo "OK: $passed checks passed"
  exit 0
fi
printf '%s' "$failures"
echo "$failed check(s) failed, $passed passed"
exit 1
