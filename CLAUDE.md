# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Dry-run on a file or directory (default — no changes made)
python srtautoedit.py -c settings.yaml -v /path/to/file.srt

# Apply changes
python srtautoedit.py -c settings.yaml -a /path/to/file.srt

# Dry-run a single rule across a real library before committing it to the config
python srtautoedit.py -c settings.yaml --only-rule "Remove formatting" -v /media/TV/

# List all rules loaded from a config
python srtautoedit.py -c settings.yaml -r

# Run tests
make test

# Rebuild Docker image (required after changing srtautoedit.py or the test scripts)
make build

# Regenerate expected test outputs after changing test/data/settings.yaml
make generate-expected

# Interactive dry-run against all test input files
make dry-run-all
```

Python formatting uses Black (enforced via pre-commit). Shell scripts are linted with shellcheck (warning level).

## Architecture

The entire tool is a single script: `srtautoedit.py`. There are no modules or packages.

**Execution flow:**
1. `parse_args()` → `load_config()` loads the YAML config and any additional rule files from `rules_directory`
2. `validate_rules()` checks each rule has required fields, a valid regex pattern, and a name that is unique across every loaded file. It reports **every** bad rule in one pass, then `main()` exits 1 without processing any files. It reads all rule fields with `.get()` — a rule missing a field is the case it exists to report, so nothing may `KeyError` ahead of the report.
3. For each SRT path argument: files are processed directly; directories are walked recursively for `*.srt` files
4. `parse_srt()` handles each file: parses it with the `srt` library, applies every rule in order to each subtitle entry's `content` field, then writes back (unless dry-run)

**Rule application in `parse_srt()`:**
- Rules run sequentially on each subtitle entry. Once an entry is deleted (`new_subtitle = None`), remaining rules are skipped for it.
- `only_if_match` uses `fnmatch.fnmatch` against the file path — case-sensitive, glob-style.
- Regex rules use `re.MULTILINE` (not `re.DOTALL`), so `.` doesn't match newlines.
- A `replace` rule that reduces `content` to `""` causes the entry to be excluded from output (same effect as `delete` but counted as a modification, not a removal). It is reported as `+  (empty — cue dropped from output)`.
- `\s` matches the newline, so `[\s]{2,}` → `" "` joins two lines when the first ends in trailing whitespace. `test/data/input/multiline.srt` cue 7 pins this.
- Files are read with universal newlines and written with `\n`, so a CRLF file is silently converted to LF — but only if some rule actually matched, since an unchanged file is never written. `test/data/edge/crlf.srt` pins this.
- If no cues remain, the file is deleted. This is checked **before** the write branch; when it was checked after, a file every cue was removed from got written back at 0 bytes.
- Otherwise the file is written when `result["modified"] != 0`, `result["removed"] != 0`, or `new_subtitle_file != original_subtitles` (catches reindex-only changes).
- `parse_srt()` returns `{"modified", "removed", "changed", "deleted", "rule_counts"}`, or `None` if the file couldn't be read or parsed. `main()` folds each result into run-level totals via `tally()`.

**Output** (see readme.md for the user-facing description):
- A single `verbosity` int threads through everything: `V_QUIET` (-1) through `V_RULES` (3). `-v` is `action="count"`; `-q` forces -1. Every print site is gated on `verbosity >= V_*`.
- Files with no changes print nothing below `V_FILES`, so output length tracks change count rather than file count.
- `print_change()` is the single writer for both the modified and removed paths, which keeps the `| rules:` attribution line to one spelling.
- Rule fire counts are keyed on `name` alone. That's only sound because `validate_rules()` rejects duplicate names; keying on `(name, from_file)` previously let two same-named rules in one file collapse into a single counter and report more affected cues than the file had.
- The rollup tags a rule with `[from <file>]` when its `from_file` differs from the config path passed to `-c`, i.e. only for rules pulled in via `rules_directory`.
- The never-fired *count* prints at `V_NORMAL`, but the *names* need `--show-rules`. That list is as long as the config rather than as long as the run, so at default verbosity a single-file post-process run against a 70-rule config printed 25 lines of rule names under a one-line summary. It hangs off `-r` and not off a verbosity level deliberately: `-v` and `-vvv` are used routinely to look at changes and must not drag the config along, and `-r` is then the way to audit for dead rules over a whole library without a change block per changed cue. Both branches are covered by the console baselines: `show-rules-rollup` takes the list, `default-verbosity` and `missing-path` take the hint line. (`no-arguments` reaches neither — it exits before the rollup, as does the pathless `show-rules` case.)
- `print_totals()` always runs, including under `-q`, and is always the last line. `files_failed` counts unreadable/unparseable files and nonexistent path arguments; without it a sweep where every file failed reported a clean `TOTAL:` line.
- `-s`/`--summary` is accepted but ignored. It cannot be removed: every post-process wrapper script passes it (`bazarr`, `sonarr`, `radarr`, `sickbeard_mp4_automator`, and both nzbget scripts via their default `SCRIPT_ARGS`), and argparse would reject the run.

**Docker / testing setup** (in `test/`):

Configs:
- `test/data/settings.yaml` — self-contained test config, one rule per behaviour with no redundancy: every rule type/action combination, a capture group in a replacement, `only_if_match` in both directions, and anchored rules that show `re.MULTILINE` behaviour. All 11 rules fire over a full-directory run and all 11 are load-bearing (see the clobbering guard below). All domains and release groups in the fixtures are invented — `.example` is reserved by RFC 2606 — so don't reintroduce real ones.
- Rules see each other's output, so one can mask another. `Remove spaces at end of line` is the live example: `Remove extra spaces` (`[\s]{2,}`) runs first and eats any trailing whitespace that sits before a newline, so the only thing that reaches `\s+$` is a single trailing space at the very end of a cue — which is what `multiline.srt` cue 9 is for. Reordering those two rules, or dropping that cue, silently guts the rule.
- `test/data/invalid-settings.yaml` — one rule per validation failure mode
- `test/data/settings-rules-dir.yaml` + `test/data/rules.d/` — the `rules_directory` path: sorted load order, `.yml`/`.yaml` filtering, a non-YAML file that must be ignored, and rules from outside the main config so the rollup has to print `[from <file>]` for them and not for the parent config's own rule
- `test/data/duplicate-settings.yaml` — a duplicate rule name within one file, and another duplicated against `rules.d/`

Fixtures:
- `test/data/input/` — files that survive apply mode, plus `nested/deep.srt` (only reachable by directory walk) and `notes.txt` (must be skipped). `multiline.srt` is built from cue structures taken verbatim from real subtitles under `/mnt/media` — italics spanning two lines, a two-speaker cue, a sound tag above dialogue, a bare `♪` above a lyric, accented text, a `<Font\ncolor=…>` tag split across a newline (matched by neither the non-DOTALL pattern nor its case-sensitivity), and trailing whitespace that joins two lines.
- `test/data/edge/` — files needing bespoke assertions: `all-removed.srt` (deleted), `crlf.srt` (CRLF→LF), `reindex.srt` (sort/reindex-only), `broken.srt` (unparseable), `rules-dir-target.srt`
- Baselines: `expected/` (subtitle content), `expected-output/` (console logs), `expected-edge/` (apply-mode edge results)

Scripts:
- `test/cases.sh` — shared list of console-output cases as `label|expected_exit|args...`, sourced by both scripts so they can't drift. Pipe-separated because rule names contain spaces. Every case is a dry-run or error path, so all are safe against the read-only mount.
- `test/run-tests.sh` — apply-mode content diff; console-output diff with exit code and no-traceback assertions; dry-run leaves every input byte-identical; a second apply pass changes nothing; the anti-clobbering guard; the four `edge/` cases
- The anti-clobbering guard walks `-r` output and, for each rule, checks that `--only-rule <name>` affects at least one cue and that `--skip-rule <name>` changes the applied result. The first catches a rule whose fixture coverage has disappeared; the second catches a rule that is redundant or is being masked by one that runs earlier.
- `test/generate-expected.sh` — regenerates all three baseline directories
- Console baselines contain file paths, so they only stay stable because those cases dry-run against the files in place. `main()` sorts `os.walk` filenames for the same reason.
- All three scripts are copied flat into `/app/` at build time, so `Dockerfile` needs updating when a new one is added.
- The `srt-auto-edit`, `test`, and `generate-expected` Docker Compose services all mount `test/data/settings.yaml` as `/config/settings.yaml` and the scripts are copied flat into `/app/` at build time
