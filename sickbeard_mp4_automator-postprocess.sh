#!/bin/bash
set -euo pipefail

# Run srt-auto-edit against any subtitle files included for sickbeard_mp4_automator

files=$(echo "${MH_FILES%%,*}" | sed 's/[]"[]//g')

for file in "${files%%.*}"* ; do
  if [[ $file == *srt ]];
  then
    /home/matt/srt-auto-edit/srtautoedit.py -c /home/matt/srt-auto-edit/settings.yaml -q -s "${file}"
  fi
done
