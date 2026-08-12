# SRTAutoEdit

Apply a set of rules to your subtitle (SRT) files. You can remove formatting, remove/replace certain words or remove whole entries.

## Installation

1. Clone the repo
2. Install dependencies (`pip3 install -r requirements.txt`)
3. Optionally, install a post-process script by copying it to the appropriate folder and editing the file (except for nzbget scripts)
4. Copy `settings.example.yaml` to `settings.yaml` and modify the rules

## Manual usage

You can manually run `srtautoedit.py` from the command line.

```
$ ./srtautoedit.py --help
usage: srtautoedit.py [-h] [--apply-changes] [--config CONFIG] [--summary]
                      [--show-rules] [--only-rule NAME] [--skip-rule NAME]
                      [--quiet | --verbose]
                      [srt ...]

Automatically apply a set of rules to subtitle(srt) files

positional arguments:
  srt                   One or more subtitle files or directories to operate
                        on

options:
  -h, --help            show this help message and exit
  --apply-changes, -a   The default is to do a dry-run. You must specify this
                        option to apply the changes!
  --config CONFIG, -c CONFIG
                        Specify the path to the settings configuration file
                        (defaults to settings.yaml)
  --summary, -s         Deprecated and ignored; per-file summaries for changed
                        files are now printed by default
  --show-rules, -r      Show all the rules and their source file
  --only-rule NAME      Only apply the rule with this name. Repeatable. Errors
                        if no rule matches
  --skip-rule NAME      Apply every rule except the one with this name.
                        Repeatable. Errors if no rule matches
  --quiet, -q           Quiet output. Only errors and the final TOTAL line
                        will be printed on screen
  --verbose, -v         Verbose output. Repeatable: -v shows changed lines,
                        -vv shows every file scanned including unchanged ones,
                        -vvv shows per-rule detail
```

Please note, the default action is a dry-run! You _must_ specify `--apply-changes` to make changes to the subtitle file(s). The first line of output always says which mode you are in.

## Output

Files that nothing matched print nothing at all, so the length of a run's output is roughly the number of changes it made.

### Verbosity

`--verbose` is repeatable, and each level adds to the one below it.

| Level | Flags | What it adds |
| ----- | ----- | ------------ |
| | `-q` | Errors and the final `TOTAL:` line only |
| | *(none)* | Banner, a `Summary:` line per **changed** file, the rule rollup |
| 1 | `-v` | `-`/`+` change blocks |
| 2 | `-vv` | A trace of every file scanned, including unchanged ones |
| 3 | `-vvv` | Per-rule detail: rules skipped by `only_if_match`, and each rule's intermediate result within a cue |

### Change blocks

Each change is prefixed with `path:cue_index` and the cue's timestamps, so a change can be found and jumped to without scrolling back for the file name.

```
/media/TV/Example Show/S05E01.srt:127  00:04:12,340 --> 00:04:15,110  [modified]
-  ####[Organ music]
+  [Organ music]
| rules: strip-hash-prefix

/media/TV/Example Show/S05E01.srt:143  00:05:01,000 --> 00:05:03,200  [removed]
-  Subtitles by subhub.example
| rules: ad-removal
```

The cue index is the index in the file as it is on disk, before any re-indexing. `| rules:` lists every rule that touched the cue, in the order they ran. A `replace` rule that empties a cue drops it from the output entirely, and is reported as `+  (empty — cue dropped from output)`.

Useful greps: `^\| rules:` for attribution, `\.srt:[0-9]+ ` for change headers.

### Rule rollup

Every run ends with a count of how many cues each rule affected, largest first. This is the quickest way to spot a new rule that is far more aggressive than intended. Rules that were loaded but never matched anything are listed after it, which catches dead or misspelled rules.

```
=== Rules fired (cues affected) ===
    512  strip-hash-prefix
     88  ad-removal [from ./rules.d/10-ads.yml]
     12  fix-ellipsis
=== Rules loaded but never fired (3) ===
     hi-speaker-tags, srt-color-strip, dvd-artifact [from ./rules.d/20-dvd.yml]
```

Rules pulled in from `rules_directory` are tagged with the file they came from. Rules defined in the main config file are not.

### The `TOTAL:` line

The last line of every run, printed at every verbosity including `--quiet`:

```
TOTAL: mode=dry-run files_scanned=9412 files_changed=318 cues_modified=1204 cues_removed=87 files_deleted=2 files_failed=1 rules_fired=9
```

`grep '^TOTAL:'` gives a single regression signal for a scheduled run. `files_failed` counts files that couldn't be read or parsed, plus paths given on the command line that don't exist. A file that fails doesn't stop the run or change the exit code, so this is the only place it shows up in a summary.

### Testing a single rule

Before adding a rule to a config that runs over a whole library, dry-run just that rule against the real files:

```
$ ./srtautoedit.py -c settings.yaml --only-rule "Remove formatting" -v /media/TV/
```

`--only-rule` and `--skip-rule` are both repeatable, and both exit non-zero if the name given doesn't match a loaded rule, so a typo can't silently turn into a no-op run.

## The `settings.yaml` file format

You can specify a directory to load multiple rules files from with the `rules_directory` option. Like so:

`rules_directory: ./rules.d`

Each rule is in the following format under the `rules:` heading.

```
- name: Remove formatting
  type: regex
  pattern: '</?(font|b|i).*?>'
  action: replace
  value: ""
```

- `name` is the name of the rule. It **must be unique** across every file that gets loaded, including anything pulled in from `rules_directory` — a duplicate is a configuration error and stops the run. It's used when reporting errors and changes, in the rule rollup, when listing all the rules loaded, and to select a rule with `--only-rule`.
- `type` is the type of rule. `regex` and `string` are the only types supported.
- `pattern` is the regex or string search value to look for. Check your regex on a site such as regex101.com or something similar.
- `action` determines what to do with the match. `replace` and `delete` are the available actions. `delete` will remove the subtitle entry.
- `value` is what to replace the match with when using the replace action.
- `only_if_match` optionally, only run the rule against file names that match this pattern (`*/tv/*` or `*/Show Name/*`) Case is important!

Rules run in the order they are loaded, and each one sees the output of the rules before it. That means a rule can mask a later one by consuming the text it was meant to match — a rule that collapses runs of whitespace will leave nothing for a rule that strips trailing whitespace, for example. `--only-rule` is the quickest way to check a rule still does what you think on its own.

Two things worth knowing about how rules apply to a whole cue:

- Regex rules use `re.MULTILINE`, and **not** `re.DOTALL`. On a cue with two lines, `^` and `$` match at each line, so an anchored rule affects only the line it matched — but `.` never matches the newline, so a rule can't match across the line break. A tag split over two lines (`<font\ncolor="#fff">`) will not be matched by a pattern like `</?(font|b|i|u).*?>`.
- `\s` does match the newline. A pattern like `[\s]{2,}` replaced with a single space will join two lines together if the first one ends in trailing whitespace.

If every cue in a file is removed, the file is deleted rather than being written back out empty.

Rules are validated before any file is touched. If a rule is missing a field, has an invalid regex, or has an unknown `type` or `action`, every problem found is printed and the run stops with exit code 1 without processing any subtitles.

Be sure to test your settings file with the `--verbose`, `--only-rule` and/or `--show-rules` command line options!
