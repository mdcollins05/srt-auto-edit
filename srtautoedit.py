#!/usr/bin/env python3

import argparse
import os.path
import re
import sys

import srt
import yaml


def main():
    settingsYaml = {}

    argsparser = argparse.ArgumentParser(
        description="Automatically apply a set of rules to srt files"
    )
    argsparser.add_argument("srt", help="SRT file or directory to operate on")
    argsparser.add_argument(
        "--config",
        "-c",
        default="settings.yaml",
        help="Specify the path to the settings configuration file",
    )
    argsparser.add_argument(
        "--summary",
        "-s",
        action="store_true",
        help="Provide a summary of what has changed",
    )
    argsparser.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Dry run. This will not make any changes and instead will tell you what it would do",
    )
    argsparser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Quiet output. Only errors will be printed on screen",
    )
    argsparser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output. Lines that have changed will be printed on screen",
    )

    args = argsparser.parse_args()

    if os.path.isfile(args.config):
        settingsFile = open(args.config)
        settingsYaml = yaml.safe_load(settingsFile)
        settingsFile.close()
    else:
        print("Couldn't open configuration file '{0}'".format(args.config))
        return False

    if len(settingsYaml) > 0:
        validate_rules(settingsYaml)
    else:
        print(
            "You don't have any rules specified in your configuration file '{0}'".format(
                args.config
            )
        )
        return False

    if os.path.isfile(args.srt):
        parse_srt(
            settingsYaml, args.srt, args.summary, args.dry_run, args.quiet, args.verbose
        )
    elif os.path.isdir(args.srt):
        for root, dirs, files in os.walk(args.srt):
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
        print("Subtitle file/path '{0}' doesn't exist".format(args.srt))


def parse_srt(settings, file, summary, dry_run, quiet, verbose):
    if dry_run or verbose or summary:
        print("Parsing '{0}'...".format(file))

    try:
        original_subtitles = None
        with open(file, "r", encoding="utf-8") as filehandler:
            original_subtitles = filehandler.read()
    except:
        print("Couldn't open file '{0}'".format(file))
        return False

    # Temporary fix until https://github.com/cdown/srt/issues/55 is fixed
    original_subtitles = original_subtitles.replace("9999\n00:00:0,500 --> 00:00:2,00\n<font color=\"#ffff00\" size=14>www.tvsubtitles.net</font>", "")

    try:
        original_subtitles = list(srt.parse(original_subtitles))
    except:
        print("Trouble parsing subtitles in '{0}'".format(file))
        # print(sys.exc_info()[0])
        return False

    new_subtitle_file = list()
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
            proprietary=original_subtitles[1].proprietary,
        )

        for rule in settings:
            if new_subtitle is None:
                break

            if rule["type"] == "regex":
                if rule["action"] == "replace":
                    new_subtitle.content = re.sub(
                        rule["pattern"],
                        rule["value"],
                        new_subtitle.content,
                        re.MULTILINE,
                    )
                elif rule["action"] == "delete":
                    if re.findall(rule["pattern"], new_subtitle.content, re.MULTILINE):
                        new_subtitle = None
                else:
                    print("Unknown action: {0}".format(rule["action"]))
            elif rule["type"] == "string":
                if rule["action"] == "replace":
                    new_subtitle.content.replace(rule["pattern"], rule["value"])
                elif rule["action"] == "delete":
                    if new_subtitle.content.find(rule["pattern"]) == -1:
                        new_subtitle = None
                else:
                    print("Error in rule: {0}".format(rule["name"]))
                    print("Unknown action: {0}".format(rule["action"]))
            else:
                print("Error in rule: {0}".format(rule["name"]))
                print("Unknown type: {0}".format(rule["type"]))

        if new_subtitle is not None:
            if new_subtitle.content != "":
                new_subtitle_file.append(new_subtitle)
                if new_subtitle.content != original_subtitle_text:
                    modified_line_count += 1
                    if dry_run or verbose:
                        if not quiet:
                            print("|Original text")
                            print("  {0}".format(original_subtitle_text))
                            print("|New text")
                            print("  {0}".format(new_subtitle.content))
                            print("|By {0}".format(rule["name"]))
        else:
            removed_line_count += 1
            if dry_run or verbose:
                if not quiet:
                    print("|Removed text")
                    print("  {0}".format(original_subtitle_text))
                    print("|By {0}".format(rule["name"]))

    if not dry_run:
        if modified_line_count != 0 or removed_line_count != 0:
            if not quiet or verbose:
                print("Saving subtitle file {0}...".format(file))
            new_subtitle_file = list(srt.sort_and_reindex(new_subtitle_file))
            with open(file, "w", encoding="utf-8") as filehandler:
                filehandler.write(srt.compose(new_subtitle_file))
        else:
            if not quiet or verbose:
                print("No changes to save")

    if summary or verbose:
        print(
            "Summary: {0} Lines modified; {1} Lines removed; '{2}'".format(
                modified_line_count, removed_line_count, file
            )
        )

    return True


def validate_rules(settings):
    # TODO: Add more validation for all the expected fields and rule types
    for rule in settings:
        if type == "regex":
            compile_regex(rule["pattern"])


def compile_regex(regex):
    try:
        return re.compile(regex, re.IGNORECASE)
    except re.error:
        print("Error with regex: {0}".format(regex))


if __name__ == "__main__":
    sys.exit(main())
