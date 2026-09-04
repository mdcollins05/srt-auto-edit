#!/bin/bash
set -euo pipefail

# shellcheck source=cases.sh
. /app/cases.sh

EXPECTED_DIR=/test-data/expected
EXPECTED_OUTPUT_DIR=/test-data/expected-output
EXPECTED_EDGE_DIR=/test-data/expected-edge
PASS=0
FAIL=0

pass() {
    echo "PASS: $1"
    PASS=$((PASS + 1))
}

fail() {
    echo "FAIL: $1"
    FAIL=$((FAIL + 1))
}

# Compares a file against a committed baseline.
diff_against() {
    local label="$1" actual="$2" expected="$3"

    if [ ! -f "$expected" ]; then
        fail "$label (no baseline — run 'make generate-expected' first)"
    elif diff -q "$actual" "$expected" >/dev/null 2>&1; then
        pass "$label"
    else
        fail "$label"
        diff "$expected" "$actual" || true
    fi
}

echo "--- Subtitle content (apply mode) ---"

for input_file in "$INPUT_DIR"/*.srt; do
    filename=$(basename "$input_file")
    tmp_file="/tmp/$filename"

    cp "$input_file" "$tmp_file"
    python /app/srtautoedit.py -a -q -c "$CONFIG" "$tmp_file" >/dev/null 2>&1 || true
    diff_against "$filename" "$tmp_file" "$EXPECTED_DIR/$filename"
    rm -f "$tmp_file"
done

echo ""
echo "--- Console output ---"

while IFS='|' read -r label expected_exit args; do
    [ -n "$label" ] || continue
    IFS='|' read -r -a case_args <<<"$args"

    tmp_log="/tmp/$label.log"
    set +e
    python /app/srtautoedit.py "${case_args[@]}" >"$tmp_log" 2>&1
    actual_exit=$?
    set -e

    if [ "$actual_exit" -ne "$expected_exit" ]; then
        fail "$label.log (expected exit $expected_exit, got $actual_exit)"
        cat "$tmp_log"
    elif grep -q "Traceback" "$tmp_log"; then
        fail "$label.log (produced a traceback)"
        cat "$tmp_log"
    else
        diff_against "$label.log" "$tmp_log" "$EXPECTED_OUTPUT_DIR/$label.log"
    fi
    rm -f "$tmp_log"
done < <(output_cases)

echo ""
echo "--- Dry-run leaves files untouched ---"

dry_run_clean=true
for input_file in "$INPUT_DIR"/*.srt; do
    filename=$(basename "$input_file")
    tmp_file="/tmp/dry-$filename"

    cp "$input_file" "$tmp_file"
    python /app/srtautoedit.py -vv -c "$CONFIG" "$tmp_file" >/dev/null 2>&1 || true
    if ! diff -q "$tmp_file" "$input_file" >/dev/null 2>&1; then
        fail "dry-run modified $filename"
        dry_run_clean=false
    fi
    rm -f "$tmp_file"
done
if [ "$dry_run_clean" = true ]; then
    pass "dry-run left every input file byte-identical"
fi

echo ""
echo "--- Applying twice is idempotent ---"

idempotent=true
for input_file in "$INPUT_DIR"/*.srt; do
    filename=$(basename "$input_file")
    once="/tmp/once-$filename"
    twice="/tmp/twice-$filename"

    cp "$input_file" "$once"
    python /app/srtautoedit.py -a -q -c "$CONFIG" "$once" >/dev/null 2>&1 || true
    cp "$once" "$twice"
    python /app/srtautoedit.py -a -q -c "$CONFIG" "$twice" >/dev/null 2>&1 || true
    if ! diff -q "$once" "$twice" >/dev/null 2>&1; then
        fail "second apply changed $filename again"
        diff "$once" "$twice" || true
        idempotent=false
    fi
    rm -f "$once" "$twice"
done
if [ "$idempotent" = true ]; then
    pass "a second apply pass changed nothing"
fi

echo ""
echo "--- Rules don't clobber each other ---"

# Rules run in order against the same content, so one can silently mask
# another by consuming the text it was meant to match. Two properties keep the
# test config honest: every rule must change something when it runs alone, and
# removing any single rule must change the result. A rule that fails the second
# check is dead weight, or is being masked by a rule that runs before it.
rules_base=/tmp/rules-base
rm -rf "$rules_base"
cp -r "$INPUT_DIR" "$rules_base"
python /app/srtautoedit.py -a -q -c "$CONFIG" "$rules_base" >/dev/null 2>&1 || true

inert=""
masked=""
while IFS= read -r rule_name; do
    [ -n "$rule_name" ] || continue

    affected=$(python /app/srtautoedit.py -c "$CONFIG" --only-rule "$rule_name" "$INPUT_DIR" 2>/dev/null |
        sed -n 's/.*cues_modified=\([0-9]*\) cues_removed=\([0-9]*\).*/\1+\2/p')
    if [ "$((${affected:-0}))" -eq 0 ]; then
        inert="$inert
    $rule_name"
    fi

    rules_skip=/tmp/rules-skip
    rm -rf "$rules_skip"
    cp -r "$INPUT_DIR" "$rules_skip"
    python /app/srtautoedit.py -a -q -c "$CONFIG" --skip-rule "$rule_name" "$rules_skip" \
        >/dev/null 2>&1 || true
    if diff -rq "$rules_base" "$rules_skip" >/dev/null 2>&1; then
        masked="$masked
    $rule_name"
    fi
    rm -rf "$rules_skip"
done < <(python /app/srtautoedit.py -r -c "$CONFIG" | sed -n 's/^Rule name: //p')
rm -rf "$rules_base"

if [ -n "$inert" ]; then
    fail "no fixture exercises these rules on their own:$inert"
else
    pass "every rule changes something when run on its own"
fi

if [ -n "$masked" ]; then
    fail "removing these rules changes nothing, so another rule masks them:$masked"
else
    pass "removing any single rule changes the result"
fi

echo ""
echo "--- Apply-mode edge cases ---"

# Every cue removed: the file must be deleted, not written back at 0 bytes.
tmp_file=/tmp/all-removed.srt
cp "$EDGE_DIR/all-removed.srt" "$tmp_file"
all_removed_log=/tmp/all-removed.log
python /app/srtautoedit.py -a -c "$CONFIG" "$tmp_file" >"$all_removed_log" 2>&1 || true
if [ -f "$tmp_file" ]; then
    fail "all-removed.srt left on disk ($(wc -c <"$tmp_file") bytes) instead of deleted"
    rm -f "$tmp_file"
elif ! grep -q "files_deleted=1" "$all_removed_log"; then
    fail "all-removed.srt deleted but TOTAL didn't report files_deleted=1"
    cat "$all_removed_log"
else
    pass "all cues removed deletes the file and reports files_deleted=1"
fi
rm -f "$all_removed_log"

# CRLF input: Python's universal newlines mean the file is rewritten with LF.
tmp_file=/tmp/crlf.srt
cp "$EDGE_DIR/crlf.srt" "$tmp_file"
python /app/srtautoedit.py -a -q -c "$CONFIG" "$tmp_file" >/dev/null 2>&1 || true
diff_against "crlf.srt (rewritten as LF)" "$tmp_file" "$EXPECTED_EDGE_DIR/crlf.srt"
rm -f "$tmp_file"

# Out of order and misnumbered, but no rule matches.
tmp_file=/tmp/reindex.srt
cp "$EDGE_DIR/reindex.srt" "$tmp_file"
reindex_log=/tmp/reindex.log
python /app/srtautoedit.py -a -c "$CONFIG" "$tmp_file" >"$reindex_log" 2>&1 || true
if ! grep -q "Only changes to sorting and indexing found" "$reindex_log"; then
    fail "reindex.srt didn't report a sorting/indexing-only change"
    cat "$reindex_log"
else
    diff_against "reindex.srt (sorted and reindexed)" "$tmp_file" "$EXPECTED_EDGE_DIR/reindex.srt"
fi
rm -f "$tmp_file" "$reindex_log"

# Unparseable input must be reported, counted, and left alone.
tmp_file=/tmp/broken.srt
cp "$EDGE_DIR/broken.srt" "$tmp_file"
broken_log=/tmp/broken-apply.log
python /app/srtautoedit.py -a -c "$CONFIG" "$tmp_file" >"$broken_log" 2>&1 || true
if ! diff -q "$tmp_file" "$EDGE_DIR/broken.srt" >/dev/null 2>&1; then
    fail "unparseable file was modified"
elif ! grep -q "files_failed=1" "$broken_log"; then
    fail "unparseable file not counted as files_failed=1"
    cat "$broken_log"
else
    pass "unparseable file left alone and counted as files_failed=1"
fi
rm -f "$tmp_file" "$broken_log"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
