import yaml
import pysrt
import re
import argparse
import os.path
import sys


def main():
  settingsYaml = {}

  if os.path.isfile("settings.yaml"):
    settingsFile = open("settings.yaml")
    settingsYaml = yaml.safe_load(settingsFile)
    settingsFile.close()

  argsparser = argparse.ArgumentParser(description="Automatically apply a set of rules to srt files")
  argsparser.add_argument("srt", help="SRT file or directory to operate on")
  argsparser.add_argument("--dry-run", "-d", help="Dry run. This will not make any changes and instead will tell you what it would do")
  argsparser.add_argument("--verbose", "-v", help="Verbose output. Lines that have changed will be printed on screen")

  args = argsparser.parse_args()

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
  print("Parsing '{0}'...".format(file))

  try:
    subtitles = pysrt.open(file)
  except:
    print("Couldn't open file {0}".format(file)
    return

  for i in range(len(subtitles)):
    original_subtitle = subtitles[i]
    for rule in settings:
      if rule['type'] == 'regex':
        if rule['action'] == 'replace':
          subtitles[i].text = re.sub(rule['pattern'], rule['value'], subtitles[i].text, flags=re.IGNORECASE)
        elif rule['action'] == 'delete':
          pass # re.match
        else:
          print("Unknown action: {0}".format(rule['action']))
      elif rule['type'] == 'string':
        if rule['action'] == 'replace':
          pass # subtitle.replace
        elif rule['action'] == 'delete':
          pass # subtitle.find
        else:
          print("Unknown action: {0}".format(rule['action']))
      else:
        print("Unknown type: {0}".format(rule['type']))
    #Add some logic to check if changes were made here

  if not dry_run:
    subtitles.clean_indexes()
    subtitles.save(file)

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
