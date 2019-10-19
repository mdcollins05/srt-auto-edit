# SRTAutoEdit

Apply a set of rules to your SRT (subtitle) files. You can remove formatting, remove/replace certain words or remove whole entries.

## Installation

1. Clone the repo
2. Install dependencies (`pip3 install -r requirements.txt`)
3. Optionally, install a post-process script by copying it to the appropriate folder and editing the file
4. Copy `settings.example.yaml` to `settings.yaml` and modify the rules

## Manual usage

You can manually run `srtautoedit.py` from the command line.

```
$ ./srtautoedit.py --help
usage: srtautoedit.py [-h] [--config CONFIG] [--summary] [--dry-run] [--quiet]
                      [--verbose]
                      srt

Automatically apply a set of rules to srt files

positional arguments:
  srt                   SRT file or directory to operate on

optional arguments:
  -h, --help            show this help message and exit
  --config CONFIG, -c CONFIG
                        Specify the path to the settings configuration file
  --summary, -s         Provide a summary of what has changed
  --dry-run, -d         Dry run. This will not make any changes and instead
                        will tell you what it would do
  --quiet, -q           Quiet output. Only errors will be printed on screen
  --verbose, -v         Verbose output. Lines that have changed will be
                        printed on screen
```

## The `settings.yaml` file format

Each rule is in the following format.

```
- name: Remove formatting
  type: regex
  pattern: '</?(font|b|i).*?>'
  action: replace
  value: ""
```

- `name` is simply the name of the rule. It isn't used for much other than for when reporting regex compilation errors and for your benefit.
- `type` is the type of rule. `regex` and `string` are the only types supported.
- `pattern` is the regex or string search value to look for. Check your regex on a site such as regex101.com or something similar.
- `action` determines what to do with the match. `replace` and `delete` are the available actions. `delete` will remove the subtitle entry.
- `value` is what to replace the match with when using the replace action.

Be sure to test your settings file with the `--dry-run` and `--verbose` command line options!
