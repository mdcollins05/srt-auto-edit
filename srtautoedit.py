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

  args = argsparser.parse_args()

  if os.path.isfile(args.srt):
    parse_srt(settingsYaml, args.srt)
  elif os.path.isdir(args.srt):
    for root, dirs, files in os.walk(args.srt):
      for file in files:
        if file.endswith(".srt"):
          parse_srt(settingsYaml, os.path.join(root, file), args.dry_run)
  else:
    print("'{0}' doesn't exist".format(args.srt))

def parse_srt(settings, file,):
  print("Parsing '{0}'...".format(file))
  subs = pysrt.open(file)
  #do things
  subs.save(file)

def validate_regex(settingsYaml):
  #Do some validation of any regex rules passed
  #try:
  #  re.compile(regex)
  #except re.error:
  #  #it's wrong
  pass

if __name__ == "__main__":
  sys.exit(main())
