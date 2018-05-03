#!/usr/bin/env python2

import yaml
import pysrt
import unidecode
import re
import argparse
import os.path
import sys


def main():
  settingsYaml = {}

  argsparser = argparse.ArgumentParser(description="Automatically apply a set of rules to srt files")
  argsparser.add_argument("srt", help="SRT file or directory to operate on")
  argsparser.add_argument("--config", "-c", default="settings.yaml", help="Specify an alternative location to find the settings configuration file")
  argsparser.add_argument("--summary", "-s", action="store_true", help="Provide a summary of what has changed")
  argsparser.add_argument("--dry-run", "-d", action="store_true", help="Dry run. This will not make any changes and instead will tell you what it would do")
  argsparser.add_argument("--quiet", "-q", action="store_true", help="Quiet output. Only errors will be printed on screen")
  argsparser.add_argument("--verbose", "-v", action="store_true", help="Verbose output. Lines that have changed will be printed on screen")

  args = argsparser.parse_args()

  if os.path.isfile(args.config):
    settingsFile = open(args.config)
    settingsYaml = yaml.safe_load(settingsFile)
    settingsFile.close()
  else:
    print("Couldn't open configuration file '{0}'".format(args.config))
    return False

  if os.path.isfile(args.srt):
    parse_srt(settingsYaml, args.srt, args.summary, args.dry_run, args.quiet, args.verbose)
  elif os.path.isdir(args.srt):
    for root, dirs, files in os.walk(args.srt):
      for file in files:
        if file.endswith(".srt"):
          parse_srt(settingsYaml, os.path.join(root, file), args.summary, args.dry_run, args.quiet, args.verbose)
  else:
    print("Subtitle file/path '{0}' doesn't exist".format(args.srt))

def parse_srt(settings, file, summary, dry_run, quiet, verbose):
  if dry_run or verbose or summary:
    print("Parsing '{0}'...".format(file))

  try:
    original_subtitles = pysrt.open(file)
  except:
    print("Couldn't open file '{0}'".format(file))
    return False

  new_subtitle_file = pysrt.SubRipFile()
  new_subtitle = None

  removed_line_count = 0
  modified_line_count = 0

  for i in range(len(original_subtitles)):
    original_subtitle_text = unidecode.unidecode(original_subtitles[i].text)
    new_subtitle = pysrt.SubRipItem(i, start=original_subtitles[i].start, end=original_subtitles[i].end, text=unidecode.unidecode(original_subtitles[i].text))

    for rule in settings:
      if new_subtitle is None:
        break

      if rule['type'] == 'regex':
        if rule['action'] == 'replace':
          new_subtitle.text = re.sub(rule['pattern'], rule['value'], new_subtitle.text, re.MULTILINE)
        elif rule['action'] == 'delete':
          if re.findall(rule['pattern'], new_subtitle.text, re.MULTILINE):
            new_subtitle = None
        else:
          print("Unknown action: {0}".format(rule['action']))
      elif rule['type'] == 'string':
        if rule['action'] == 'replace':
          new_subtitle.text.replace(rule['pattern'], rule['value'])
        elif rule['action'] == 'delete':
          if new_subtitle.text.find(rule['pattern']) == -1:
            new_subtitle = None
        else:
          print("Unknown action: {0}".format(rule['action']))
      else:
        print("Unknown type: {0}".format(rule['type']))

    if new_subtitle is not None:
      if new_subtitle.text != '':
        new_subtitle_file.append(new_subtitle)
        if new_subtitle.text != original_subtitle_text:
          modified_line_count += 1
          if dry_run or verbose:
            if not quiet:
              print("## Original text ####")
              print("{0}".format(original_subtitle_text))
              print("## New text #########")
              print("{0}".format(new_subtitle.text))
              print("#####################")
    else:
      removed_line_count += 1
      if dry_run or verbose:
        if not quiet:
          print("## Removed subtitle #")
          print("{0}".format(original_subtitle_text))
          print("#####################")

  if not dry_run:
    if modified_line_count != 0 or removed_line_count != 0:
      if not quiet or verbose:
        print("Saving subtitle file...")
      new_subtitle_file.clean_indexes()
      new_subtitle_file.save(file)
    else:
      if not quiet or verbose:
        print("No changes to save")


  if summary or verbose:
    print("## Summary ##")
    print("{0} Lines removed".format(removed_line_count))
    print("{0} Lines modified".format(modified_line_count))
    print("#####################")

  return True

def validate_regex(settings):
  for rule in settings:
    if type == "regex":
      compile_regex(rule['pattern'])

def compile_regex(regex):
  try:
   return re.compile(regex, re.IGNORECASE)
  except re.error:
    print("Error with regex: {0}".format(regex))

if __name__ == "__main__":
  sys.exit(main())
