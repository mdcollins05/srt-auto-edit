#!/bin/bash
set -euo pipefail

# shellcheck source=cases.sh
. /app/cases.sh

EXPECTED_DIR=/test-data/expected
EXPECTED_OUTPUT_DIR=/test-data/expected-output
EXPECTED_EDGE_DIR=/test-data/expected-edge

mkdir -p "$EXPECTED_DIR" "$EXPECTED_OUTPUT_DIR" "$EXPECTED_EDGE_DIR"

for input_file in "$INPUT_DIR"/*.srt; do
    filename=$(basename "$input_file")
    tmp_file="/tmp/$filename"

    cp "$input_file" "$tmp_file"
    python /app/srtautoedit.py -a -q -c "$CONFIG" "$tmp_file" >/dev/null 2>&1 || true
    cp "$tmp_file" "$EXPECTED_DIR/$filename"
    echo "Generated: expected/$filename"
    rm -f "$tmp_file"
done

# The expected exit code is only asserted by run-tests.sh; here the baseline is
# generated whatever the run exits with.
while IFS='|' read -r label _ args; do
    [ -n "$label" ] || continue
    IFS='|' read -r -a case_args <<<"$args"

    python /app/srtautoedit.py "${case_args[@]}" \
        >"$EXPECTED_OUTPUT_DIR/$label.log" 2>&1 || true
    echo "Generated: expected-output/$label.log"
done < <(output_cases)

# Apply-mode edge cases that produce a file to compare against.
for filename in crlf.srt reindex.srt; do
    tmp_file="/tmp/$filename"
    cp "$EDGE_DIR/$filename" "$tmp_file"
    python /app/srtautoedit.py -a -q -c "$CONFIG" "$tmp_file" >/dev/null 2>&1 || true
    cp "$tmp_file" "$EXPECTED_EDGE_DIR/$filename"
    echo "Generated: expected-edge/$filename"
    rm -f "$tmp_file"
done

echo ""
echo "Baselines written to $EXPECTED_DIR, $EXPECTED_OUTPUT_DIR and $EXPECTED_EDGE_DIR"
echo "Review the outputs and commit them to lock in the baseline."
