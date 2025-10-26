#!/usr/bin/env python3

import argparse
import fnmatch
import os.path
import re
import sys
import textwrap

import srt
import yaml


def main():
    settingsYaml = {}

    args = parse_args()

    settingsYaml = load_config(args.config)

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
                    if len(rules) > 0:
                        settingsYaml["rules"].extend(tag_rules(rules, full_file_path))

    if len(settingsYaml) > 0:
        validate_rules(settingsYaml["rules"])
    else:
        print(
            "You don't have any rules specified in your configuration file '{0}'".format(
                args.config
            )
        )
        return False

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

    for srt in args.srt:
        if args.show_rules:
            print()
        if os.path.isfile(srt):
            parse_srt(
                settingsYaml, srt, args.summary, args.dry_run, args.quiet, args.verbose
            )
        elif os.path.isdir(srt):
            for root, dirs, files in os.walk(srt):
                for file in files:
                    if file.endswith(".srt"):
                        parse_srt(
                            settingsYaml,
                            os.path.join(root, file),
                            args.summary,
                            args.dry_run,
                            args.quiet,
                            args.verbose,
                        )
        else:
            print("Subtitle file/path '{0}' doesn't exist".format(srt))

    if not args.show_rules and len(args.srt) == 0:
        print()
        print("No subtitle files or directories specified.")


def parse_srt(settings, file, summary, dry_run, quiet, verbose):
    if dry_run or verbose:
        print("Parsing '{0}'...".format(file))

    try:
        original_subtitles = None
        with open(file, "r", encoding="utf-8") as filehandler:
            original_subtitles = filehandler.read()
    except:
        print()
        print("Couldn't open file '{0}'".format(file))
        return False

    try:
        original_subtitles = list(srt.parse(original_subtitles))
    except:
        print()
        print("Trouble parsing subtitles in '{0}'".format(file))
        return False

    new_subtitle_file = []
    new_subtitle = None

    removed_line_count = 0
    modified_line_count = 0

    for i in range(len(original_subtitles)):
        original_subtitle_text = original_subtitles[i].content
        new_subtitle = srt.Subtitle(
            i,
            start=original_subtitles[i].start,
            end=original_subtitles[i].end,
            content=original_subtitles[i].content,
            proprietary=original_subtitles[i].proprietary,
        )

        line_history = []

        for rule in settings["rules"]:
            if new_subtitle is None:
                break

            if "only_if_match" in rule:
                if not fnmatch.fnmatch(file, rule["only_if_match"]):
                    continue

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
                    new_subtitle.content = new_subtitle.content.replace(rule["pattern"], rule["value"])
                elif rule["action"] == "delete":
                    if new_subtitle.content.find(rule["pattern"]) != -1:
                        new_subtitle = None

            if new_subtitle is None:
                line_history.append(rule["name"])
            elif new_subtitle.content != line_before_rule_run:
                line_history.append(rule["name"])

        if new_subtitle is not None:
            if new_subtitle.content != "":
                new_subtitle_file.append(new_subtitle)
            if new_subtitle.content != original_subtitle_text:
                modified_line_count += 1
                if verbose:
                    if not quiet:
                        print()
                        print("{0}".format(wrap_sub(original_subtitle_text, "-")))
                        print("{0}".format(wrap_sub(new_subtitle.content, "+")))
                        print(
                            "|By rule(s): {0}".format(", ".join(map(str, line_history)))
                        )
        else:
            removed_line_count += 1
            if verbose:
                if not quiet:
                    print()
                    print("{0}".format(wrap_sub(original_subtitle_text, "-")))
                    print("|By rule: {0}".format(line_history[-1]))

    if not dry_run:
        new_subtitle_file = list(srt.sort_and_reindex(new_subtitle_file))
        if (
            modified_line_count != 0
            or removed_line_count != 0
            or new_subtitle_file != original_subtitles
        ):
            print()
            if modified_line_count == 0 and removed_line_count == 0 and not quiet:
                print(
                    "Only changes to sorting and indexing found; No changes to subtitles detected."
                )
            if not quiet or verbose:
                print("Saving subtitle file {0}...".format(file))
                print()
            with open(file, "w", encoding="utf-8") as filehandler:
                filehandler.write(srt.compose(new_subtitle_file))
        elif len(new_subtitle_file) == 0:
            if not quiet or verbose:
                print("Deleting empty subtitle file {0}...".format(file))
                print()
            os.remove(file)
        else:
            if not quiet or verbose:
                print("No changes to save")
                print()

    if summary or verbose:
        if dry_run:
            if verbose:
                print()
            print(
                "Summary: {0} Lines to be modified; {1} Lines to be removed; '{2}'".format(
                    modified_line_count, removed_line_count, file
                )
            )
        else:
            print(
                "Summary: {0} Lines modified; {1} Lines removed; '{2}'".format(
                    modified_line_count, removed_line_count, file
                )
            )
        print()

    return True


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
        "--summary", "-s", action="store_true", help="Provide a summary of the changes"
    )
    argsparser.add_argument(
        "--show-rules",
        "-r",
        action="store_true",
        help="Show all the rules and their source file",
    )
    v_q_group = argsparser.add_mutually_exclusive_group()
    v_q_group.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Quiet output. Only errors will be printed on screen",
    )
    v_q_group.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output. Lines that have been modified will be printed on screen",
    )

    return argsparser.parse_args()


def validate_rules(rules):
    errors = False
    for rule in rules:
        if rule["type"] == "regex":
            if "pattern" not in rule:
                errors = True
                rule_error(
                    rule["name"],
                    rule["from_file"],
                    "You must define the regex to find as the pattern.",
                )
            if not compile_regex(rule["pattern"]):
                errors = True
                rule_error(
                    rule["name"],
                    rule["from_file"],
                    "Regex isn't valid. Please verify it's correct. https://regex101.com/ is a good site.",
                )
        elif rule["type"] == "string":
            if "pattern" not in rule:
                errors = True
                rule_error(
                    rule["name"],
                    rule["from_file"],
                    "You must define the string to find as the pattern.",
                )
        else:
            errors = True
            rule_error(rule["name"], "Unknown rule type: {0}".format(rule["type"]))

        if rule["action"] == "replace":
            if "value" not in rule:
                errors = True
                rule_error(
                    rule["name"],
                    rule["from_file"],
                    "You must define the value to replace.",
                )
        elif rule["action"] != "delete":
            errors = True
            rule_error(
                rule["name"],
                rule["from_file"],
                "Unknown rule action: {0}".format(rule["action"]),
            )

    if errors:
        return False


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
