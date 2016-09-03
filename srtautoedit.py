#!/usr/bin/env python2

import yaml
import pysrt
import re
import argparse
import os.path
import sys


def main():
  settingsYaml = {}

  argsparser = argparse.ArgumentParser(description="Automatically apply a set of rules to srt files")
  argsparser.add_argument("srt", help="SRT file or directory to operate on")
  argsparser.add_argument("--config", "-c", default="settings.yaml", help="Specify an alternative location to find the settings configuration file")
  argsparser.add_argument("--dry-run", "-d", action="store_true", help="Dry run. This will not make any changes and instead will tell you what it would do")
  argsparser.add_argument("--verbose", "-v", action="store_true", help="Verbose output. Lines that have changed will be printed on screen")

  args = argsparser.parse_args()

  if os.path.isfile(args.config):
    settingsFile = open(args.config)
    settingsYaml = yaml.safe_load(settingsFile)
    settingsFile.close()
  else:
    print("Couldn't open configuration file")
    return False

  if os.path.isfile(args.srt):
    parse_srt(settingsYaml, args.srt, args.dry_run, args.verbose)
  elif os.path.isdir(args.srt):
    for root, dirs, files in os.walk(args.srt):
      for file in files:
        if file.endswith(".srt"):
          parse_srt(settingsYaml, os.path.join(root, file), args.dry_run, args.verbose)
  else:
    print("'{0}' doesn't exist".format(args.srt))

def parse_srt(settings, file, dry_run, verbose):
  if verbose:
    print("Parsing '{0}'...".format(file))

  try:
    original_subtitles = pysrt.open(file)
  except:
    print("Couldn't open file {0}".format(file))
    return False

  new_subtitle_file = pysrt.SubRipFile()
  new_subtitle = None
  for i in range(len(original_subtitles)):
    original_subtitle_text = original_subtitles[i].text
    new_subtitle = pysrt.SubRipItem(i, start=original_subtitles[i].start, end=original_subtitles[i].end, text=original_subtitles[i].text)
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
        if (dry_run or verbose) and new_subtitle.text != original_subtitle_text:
          print("## Original text ####")
          print("{0}".format(original_subtitle_text))
          print("## New text #########")
          print("{0}".format(new_subtitle.text))
          print("#####################")
    else:
      if dry_run or verbose:
        print("## Removed subtitle #")
        print("{0}".format(original_subtitle_text))
        print("#####################")

  if not dry_run:
    new_subtitle_file.clean_indexes()
    new_subtitle_file.save(file)

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
