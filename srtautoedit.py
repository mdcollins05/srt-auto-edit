#!/usr/bin/env python3

import argparse
import fnmatch
import os.path
import re
import sys
import textwrap
from collections import Counter

import srt
import yaml

# Verbosity ladder. Each level is additive: -vv implies -v.
#   QUIET    -q     errors and the TOTAL line only
#   NORMAL          banner, per-file summary for changed files, rule rollup
#   CHANGES  -v     -/+ change blocks with path:cue headers
#   FILES    -vv    per-file trace for every file, including unchanged ones
#   RULES    -vvv   rule-level trace: skipped rules, per-rule intermediate steps
V_QUIET = -1
V_NORMAL = 0
V_CHANGES = 1
V_FILES = 2
V_RULES = 3


def main():
    args = parse_args()

    verbosity = V_QUIET if args.quiet else args.verbosity

    settingsYaml = load_config(args.config)

    if settingsYaml is False:
        return 1

    if not isinstance(settingsYaml, dict):
        settingsYaml = {}

    if "rules" not in settingsYaml:
        settingsYaml["rules"] = []
    else:
        settingsYaml["rules"] = tag_rules(settingsYaml["rules"], args.config)

    if "rules_directory" in settingsYaml:
        dir = settingsYaml["rules_directory"]
        if os.path.isdir(dir):
            for file in sorted(os.listdir(dir)):
                full_file_path = os.path.join(dir, file)
                if file.endswith(".yml") or file.endswith(".yaml"):
                    rules = load_config(full_file_path)
                    if rules and len(rules) > 0:
                        settingsYaml["rules"].extend(tag_rules(rules, full_file_path))

    if len(settingsYaml) > 0:
        if not validate_rules(settingsYaml["rules"]):
            print()
            print("Configuration has errors; no subtitle files were processed.")
            return 1
    else:
        print(
            "You don't have any rules specified in your configuration file '{0}'".format(
                args.config
            )
        )
        return 1

    filtered_rules = filter_rules(settingsYaml["rules"], args.only_rule, args.skip_rule)
    if filtered_rules is None:
        return 1
    settingsYaml["rules"] = filtered_rules

    if verbosity >= V_NORMAL:
        print_banner(args.dry_run, args.config, len(settingsYaml["rules"]))

    if args.show_rules:
        last_from_file = ""
        for rule in settingsYaml["rules"]:
            from_file = rule["from_file"]
            if last_from_file != from_file:
                if last_from_file != "":
                    print()
                print("Below rules are from file: {0}".format(from_file))
                last_from_file = from_file
            print("Rule name: {0}".format(rule["name"]))

    if len(args.srt) == 0:
        if not args.show_rules:
            print()
            print("No subtitle files or directories specified.")
        return 0

    totals = {
        "files_scanned": 0,
        "files_changed": 0,
        "cues_modified": 0,
        "cues_removed": 0,
        "files_deleted": 0,
        "files_failed": 0,
    }
    rule_counts = Counter()

    for srt_path in args.srt:
        if args.show_rules:
            print()
        if os.path.isfile(srt_path):
            tally(
                totals,
                rule_counts,
                parse_srt(settingsYaml, srt_path, args.dry_run, verbosity),
            )
        elif os.path.isdir(srt_path):
            for root, dirs, files in os.walk(srt_path):
                for file in sorted(files):
                    if file.endswith(".srt"):
                        tally(
                            totals,
                            rule_counts,
                            parse_srt(
                                settingsYaml,
                                os.path.join(root, file),
                                args.dry_run,
                                verbosity,
                            ),
                        )
        else:
            print("Subtitle file/path '{0}' doesn't exist".format(srt_path))
            totals["files_failed"] += 1

    if verbosity >= V_NORMAL:
        print_rule_rollup(
            settingsYaml["rules"], rule_counts, args.config, args.show_rules
        )

    print_totals(totals, rule_counts, args.dry_run)

    return 0


def tally(totals, rule_counts, result):
    # A file that couldn't be read or parsed is counted, not dropped: a sweep
    # where every file failed must not report a clean TOTAL line.
    if result is None:
        totals["files_failed"] += 1
        return

    totals["files_scanned"] += 1
    totals["cues_modified"] += result["modified"]
    totals["cues_removed"] += result["removed"]
    if result["changed"]:
        totals["files_changed"] += 1
    if result["deleted"]:
        totals["files_deleted"] += 1
    rule_counts.update(result["rule_counts"])


def parse_srt(settings, file, dry_run, verbosity):
    result = {
        "modified": 0,
        "removed": 0,
        "changed": False,
        "deleted": False,
        "rule_counts": Counter(),
    }

    if verbosity >= V_FILES:
        print("Parsing '{0}'...".format(file))

    try:
        original_subtitles = None
        with open(file, "r", encoding="utf-8") as filehandler:
            original_subtitles = filehandler.read()
    except:
        print()
        print("Couldn't open file '{0}'".format(file))
        return None

    try:
        original_subtitles = list(srt.parse(original_subtitles))
    except:
        print()
        print("Trouble parsing subtitles in '{0}'".format(file))
        return None

    # only_if_match is evaluated against the file path, so a rule is either
    # active for the whole file or not at all. Report it once, not per cue.
    active_rules = []
    for rule in settings["rules"]:
        if "only_if_match" in rule and not fnmatch.fnmatch(file, rule["only_if_match"]):
            if verbosity >= V_RULES:
                print(
                    "| skip '{0}': only_if_match '{1}' doesn't match this path".format(
                        rule["name"], rule["only_if_match"]
                    )
                )
            continue
        active_rules.append(rule)

    new_subtitle_file = []
    new_subtitle = None

    for i in range(len(original_subtitles)):
        original_subtitle = original_subtitles[i]
        original_subtitle_text = original_subtitle.content
        cue_index = (
            original_subtitle.index if original_subtitle.index is not None else i + 1
        )

        new_subtitle = srt.Subtitle(
            i,
            start=original_subtitle.start,
            end=original_subtitle.end,
            content=original_subtitle.content,
            proprietary=original_subtitle.proprietary,
        )

        line_history = []

        for rule in active_rules:
            if new_subtitle is None:
                break

            line_before_rule_run = new_subtitle.content

            if rule["type"] == "regex":
                if rule["action"] == "replace":
                    new_subtitle.content = re.sub(
                        rule["pattern"],
                        rule["value"],
                        new_subtitle.content,
                        flags=re.MULTILINE,
                    )
                elif rule["action"] == "delete":
                    if re.findall(rule["pattern"], new_subtitle.content, re.MULTILINE):
                        new_subtitle = None
            elif rule["type"] == "string":
                if rule["action"] == "replace":
                    new_subtitle.content = new_subtitle.content.replace(
                        rule["pattern"], rule["value"]
                    )
                elif rule["action"] == "delete":
                    if new_subtitle.content.find(rule["pattern"]) != -1:
                        new_subtitle = None

            if new_subtitle is None:
                line_history.append(rule["name"])
                result["rule_counts"][rule["name"]] += 1
                if verbosity >= V_RULES:
                    print("| step '{0}': cue deleted".format(rule["name"]))
            elif new_subtitle.content != line_before_rule_run:
                line_history.append(rule["name"])
                result["rule_counts"][rule["name"]] += 1
                if verbosity >= V_RULES:
                    print("| step '{0}':".format(rule["name"]))
                    print(wrap_sub(new_subtitle.content, "~"))

        if new_subtitle is not None:
            if new_subtitle.content != "":
                new_subtitle_file.append(new_subtitle)
            if new_subtitle.content != original_subtitle_text:
                result["modified"] += 1
                if verbosity >= V_CHANGES:
                    print_change(
                        file,
                        cue_index,
                        original_subtitle,
                        original_subtitle_text,
                        new_subtitle.content,
                        line_history,
                        "modified",
                    )
        else:
            result["removed"] += 1
            if verbosity >= V_CHANGES:
                print_change(
                    file,
                    cue_index,
                    original_subtitle,
                    original_subtitle_text,
                    None,
                    line_history,
                    "removed",
                )

    if dry_run:
        result["changed"] = result["modified"] != 0 or result["removed"] != 0
        if len(new_subtitle_file) == 0:
            result["changed"] = True
            result["deleted"] = True
            if verbosity >= V_NORMAL:
                print("No cues remain; '{0}' would be deleted".format(file))
    else:
        new_subtitle_file = list(srt.sort_and_reindex(new_subtitle_file))
        # Checked before the write branch: a file every cue was removed from
        # would otherwise be written back out as zero bytes.
        if len(new_subtitle_file) == 0:
            result["changed"] = True
            result["deleted"] = True
            if verbosity >= V_NORMAL:
                print("No cues remain; deleting '{0}'".format(file))
            os.remove(file)
        elif (
            result["modified"] != 0
            or result["removed"] != 0
            or new_subtitle_file != original_subtitles
        ):
            result["changed"] = True
            if (
                result["modified"] == 0
                and result["removed"] == 0
                and verbosity >= V_NORMAL
            ):
                print(
                    "Only changes to sorting and indexing found; No changes to subtitles detected in '{0}'".format(
                        file
                    )
                )
            if verbosity >= V_FILES:
                print("Saving subtitle file {0}...".format(file))
            with open(file, "w", encoding="utf-8") as filehandler:
                filehandler.write(srt.compose(new_subtitle_file))
        else:
            if verbosity >= V_FILES:
                print("No changes to save")

    if verbosity >= V_FILES or (verbosity >= V_NORMAL and result["changed"]):
        if dry_run:
            print(
                "Summary: {0} Lines to be modified; {1} Lines to be removed; '{2}'".format(
                    result["modified"], result["removed"], file
                )
            )
        else:
            print(
                "Summary: {0} Lines modified; {1} Lines removed; '{2}'".format(
                    result["modified"], result["removed"], file
                )
            )

    return result


def print_banner(dry_run, config, rule_count):
    if dry_run:
        mode = "DRY RUN, no files will be written (pass -a to apply)"
    else:
        mode = "APPLYING CHANGES, files will be overwritten"

    print(
        "srt-auto-edit — {0}  |  config: {1}  |  {2} rule{3} loaded".format(
            mode, config, rule_count, "" if rule_count == 1 else "s"
        )
    )


def print_change(file, cue_index, subtitle, before, after, rules, kind):
    print()
    print(
        "{0}:{1}  {2} --> {3}  [{4}]".format(
            file,
            cue_index,
            srt.timedelta_to_srt_timestamp(subtitle.start),
            srt.timedelta_to_srt_timestamp(subtitle.end),
            kind,
        )
    )
    print("{0}".format(wrap_sub(before, "-")))
    if after == "":
        # An emptied cue is dropped from the output entirely, same end result
        # as a delete rule. Say so rather than printing a bare "+" line.
        print("+  (empty — cue dropped from output)")
    elif after is not None:
        print("{0}".format(wrap_sub(after, "+")))
    print("| rules: {0}".format(", ".join(map(str, rules))))


def print_rule_rollup(rules, rule_counts, config, show_rules):
    # Rule names are unique (validate_rules enforces it), so the name alone
    # identifies a rule. Only rules loaded from outside the main config file
    # are qualified with where they came from.
    def label(rule):
        if rule.get("from_file") != config:
            return "{0} [from {1}]".format(rule["name"], rule.get("from_file"))
        return rule["name"]

    fired = sorted(
        [
            (rule, rule_counts[rule["name"]])
            for rule in rules
            if rule_counts[rule["name"]]
        ],
        key=lambda item: (-item[1], label(item[0])),
    )
    never_fired = [label(rule) for rule in rules if not rule_counts[rule["name"]]]

    print()
    print("=== Rules fired (cues affected) ===")
    if fired:
        for rule, count in fired:
            print("{0:>7}  {1}".format(count, label(rule)))
    else:
        print("     (none)")

    if never_fired:
        print("=== Rules loaded but never fired ({0}) ===".format(len(never_fired)))
        # The list is as long as the config, not as long as the run, so a
        # single-file run against a large config would bury its own output in
        # rule names. The count is the signal; the names are the detail.
        #
        # Gated on --show-rules rather than on verbosity, because it answers a
        # question about the rules, not about the files: -v and -vvv are used
        # routinely to look at changes, and shouldn't drag the config along.
        if show_rules:
            print(
                textwrap.fill(
                    ", ".join(never_fired),
                    width=100,
                    initial_indent="     ",
                    subsequent_indent="     ",
                )
            )
        else:
            print("     (run with -r to list them)")


def print_totals(totals, rule_counts, dry_run):
    print(
        "TOTAL: mode={0} files_scanned={1} files_changed={2} cues_modified={3} "
        "cues_removed={4} files_deleted={5} files_failed={6} rules_fired={7}".format(
            "dry-run" if dry_run else "apply",
            totals["files_scanned"],
            totals["files_changed"],
            totals["cues_modified"],
            totals["cues_removed"],
            totals["files_deleted"],
            totals["files_failed"],
            len([count for count in rule_counts.values() if count > 0]),
        )
    )


def filter_rules(rules, only_rule, skip_rule):
    known_names = set(rule["name"] for rule in rules)

    for requested in (only_rule or []) + (skip_rule or []):
        if requested not in known_names:
            print(
                "No rule named '{0}' is loaded. Use -r to list rule names.".format(
                    requested
                )
            )
            return None

    filtered = rules
    if only_rule:
        filtered = [rule for rule in filtered if rule["name"] in set(only_rule)]
    if skip_rule:
        filtered = [rule for rule in filtered if rule["name"] not in set(skip_rule)]

    return filtered


def parse_args():
    argsparser = argparse.ArgumentParser(
        description="Automatically apply a set of rules to subtitle(srt) files"
    )
    argsparser.add_argument(
        "srt", nargs="*", help="One or more subtitle files or directories to operate on"
    )
    argsparser.add_argument(
        "--apply-changes",
        "-a",
        action="store_false",
        dest="dry_run",
        help="The default is to do a dry-run. You must specify this option to apply the changes!",
    )
    argsparser.add_argument(
        "--config",
        "-c",
        default="settings.yaml",
        help="Specify the path to the settings configuration file (defaults to settings.yaml)",
    )
    argsparser.add_argument(
        "--show-rules",
        "-r",
        action="store_true",
        help="Show all the rules and their source file, and name the rules that never fired in the rollup",
    )
    argsparser.add_argument(
        "--only-rule",
        action="append",
        metavar="NAME",
        help="Only apply the rule with this name. Repeatable. Errors if no rule matches",
    )
    argsparser.add_argument(
        "--skip-rule",
        action="append",
        metavar="NAME",
        help="Apply every rule except the one with this name. Repeatable. Errors if no rule matches",
    )
    v_q_group = argsparser.add_mutually_exclusive_group()
    v_q_group.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Quiet output. Only errors and the final TOTAL line will be printed on screen",
    )
    v_q_group.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        dest="verbosity",
        help="Verbose output. Repeatable: -v shows changed lines, -vv shows every file "
        "scanned including unchanged ones, -vvv shows per-rule detail",
    )

    return argsparser.parse_args()


def validate_rules(rules):
    errors = False
    seen_names = {}

    for rule in rules:
        # Names identify a rule in the rollup, in --only-rule and in error
        # messages, so they have to be unique across every file loaded.
        name = rule.get("name")
        if name is not None:
            if name in seen_names:
                errors = True
                rule_error(
                    name,
                    rule.get("from_file", "<unknown file>"),
                    "A rule named '{0}' is already defined in '{1}'. Rule names must be unique.".format(
                        name, seen_names[name]
                    ),
                )
            else:
                seen_names[name] = rule.get("from_file", "<unknown file>")

    for rule in rules:
        # Every field is read with .get() here: a rule that is missing one is
        # exactly the case this function exists to report, so it must not be
        # the case that reads it blows up first.
        name = rule.get("name", "<unnamed rule>")
        from_file = rule.get("from_file", "<unknown file>")

        if "name" not in rule:
            errors = True
            rule_error(name, from_file, "You must give the rule a name.")

        rule_type = rule.get("type")
        if rule_type == "regex":
            if "pattern" not in rule:
                errors = True
                rule_error(
                    name, from_file, "You must define the regex to find as the pattern."
                )
            elif not compile_regex(rule["pattern"]):
                errors = True
                rule_error(
                    name,
                    from_file,
                    "Regex isn't valid. Please verify it's correct. https://regex101.com/ is a good site.",
                )
        elif rule_type == "string":
            if "pattern" not in rule:
                errors = True
                rule_error(
                    name,
                    from_file,
                    "You must define the string to find as the pattern.",
                )
        elif rule_type is None:
            errors = True
            rule_error(
                name,
                from_file,
                "You must define the rule type. 'regex' and 'string' are supported.",
            )
        else:
            errors = True
            rule_error(name, from_file, "Unknown rule type: {0}".format(rule_type))

        action = rule.get("action")
        if action == "replace":
            if "value" not in rule:
                errors = True
                rule_error(name, from_file, "You must define the value to replace.")
        elif action is None:
            errors = True
            rule_error(
                name,
                from_file,
                "You must define the rule action. 'replace' and 'delete' are supported.",
            )
        elif action != "delete":
            errors = True
            rule_error(name, from_file, "Unknown rule action: {0}".format(action))

    return not errors


def tag_rules(rules, filename):
    new_rules = rules
    if len(rules) > 0:
        for i in range(len(rules)):
            new_rules[i]["from_file"] = filename

    return new_rules


def compile_regex(regex):
    try:
        return re.compile(regex, re.MULTILINE)
    except re.error:
        return False


def rule_error(rule_name, rule_file, message):
    print()
    print("Error in rule: '{0}' From: '{1}'".format(rule_name, rule_file))
    print(message)


def wrap_sub(content, prefix):
    if content == "":
        return prefix + "  (empty)"
    return textwrap.indent(content, prefix + "  ")


def load_config(config):
    if os.path.isfile(config):
        settingsFile = open(config)
        settingsYaml = yaml.safe_load(settingsFile)
        settingsFile.close()

        if not settingsYaml:
            settingsYaml = []

        return settingsYaml
    else:
        print("Couldn't open configuration file '{0}'".format(config))
        return False


if __name__ == "__main__":
    sys.exit(main())
