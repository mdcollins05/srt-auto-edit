#!/bin/bash
# Shared definition of the console-output test cases, sourced by both
# run-tests.sh and generate-expected.sh so the two can't drift apart.
#
# Every case here is a dry-run or an error path, so none of them write to
# /test-data and they are safe against a read-only mount. Apply-mode
# behaviour is asserted separately in run-tests.sh.
#
# Format, pipe separated so arguments may contain spaces:
#   <label>|<expected exit code>|<argument>|<argument>|...

CONFIG=/config/settings.yaml
RULES_DIR_CONFIG=/test-data/settings-rules-dir.yaml
INVALID_CONFIG=/test-data/invalid-settings.yaml
DUPLICATE_CONFIG=/test-data/duplicate-settings.yaml
INPUT_DIR=/test-data/input
EDGE_DIR=/test-data/edge

output_cases() {
    cat <<EOF
ads-and-credits|0|-vv|-c|$CONFIG|$INPUT_DIR/ads-and-credits.srt
clean|0|-vv|-c|$CONFIG|$INPUT_DIR/clean.srt
malformed|0|-vv|-c|$CONFIG|$INPUT_DIR/malformed.srt
multiline|0|-vv|-c|$CONFIG|$INPUT_DIR/multiline.srt
all-files|0|-vv|-c|$CONFIG|$INPUT_DIR
rule-trace|0|-vvv|-c|$CONFIG|$INPUT_DIR/multiline.srt
only-rule|0|-v|-c|$CONFIG|--only-rule|Remove formatting|$INPUT_DIR
skip-rule|0|-v|-c|$CONFIG|--skip-rule|Remove formatting|--skip-rule|Remove extra spaces|$INPUT_DIR
show-rules|0|-r|-c|$CONFIG
rules-directory|0|-vv|-c|$RULES_DIR_CONFIG|$EDGE_DIR/rules-dir-target.srt
broken|0|-vv|-c|$CONFIG|$EDGE_DIR/broken.srt
unknown-rule|1|-c|$CONFIG|--only-rule|No Such Rule|$INPUT_DIR
invalid-config|1|-c|$INVALID_CONFIG|$INPUT_DIR
duplicate-rule-names|1|-c|$DUPLICATE_CONFIG|$INPUT_DIR
missing-path|0|-c|$CONFIG|/test-data/does-not-exist.srt
no-arguments|0|-c|$CONFIG
EOF
}
