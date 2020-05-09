# SRTAutoEdit

Apply a set of rules to your subtitle (SRT) files. You can remove formatting, remove/replace certain words or remove whole entries.

## Installation

1. Clone the repo
2. Install dependencies (`pip3 install -r requirements.txt`)
3. Optionally, install a post-process script by copying it to the appropriate folder and editing the file
4. Copy `settings.example.yaml` to `settings.yaml` and modify the rules

## Manual usage

You can manually run `srtautoedit.py` from the command line.

```
$ ./srtautoedit.py --help
usage: srtautoedit.py [-h] [--apply-changes] [--config CONFIG] [--summary]
                      [--show-rules] [--quiet | --verbose]
                      [srt [srt ...]]

Automatically apply a set of rules to subtitle(srt) files

positional arguments:
  srt                   One or more subtitle(srt) files or directories to
                        operate on

optional arguments:
  -h, --help            show this help message and exit
  --apply-changes, -a   The default is to do a dry-run. You must specify this
                        option to apply the changes!
  --config CONFIG, -c CONFIG
                        Specify the path to the settings configuration file
                        (defaults to settings.yaml)
  --summary, -s         Provide a summary of what has changed
  --show-rules, -r      Show all the rules and their source file
  --quiet, -q           Quiet output. Only errors will be printed on screen
  --verbose, -v         Verbose output. Lines that have changed will be
                        printed on screen
```

Please note, the default action is a dry-run! You _must_ specify `--apply-changes` to make changes to the subtitle file(s).

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

- `name` is simply the name of the rule. It should be unique but that's not enforced. It's used when reporting errors, changes or when listing all the rules loaded.
- `type` is the type of rule. `regex` and `string` are the only types supported.
- `pattern` is the regex or string search value to look for. Check your regex on a site such as regex101.com or something similar.
- `action` determines what to do with the match. `replace` and `delete` are the available actions. `delete` will remove the subtitle entry.
- `value` is what to replace the match with when using the replace action.

Be sure to test your settings file with the `--verbose` and/or `--show-rules` command line options!
