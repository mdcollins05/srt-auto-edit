#!/bin/bash
set -euo pipefail

# Run srt-auto-edit against any subtitle files included for sickbeard_mp4_automator

SCRIPT_PATH="/home/matt/srt-auto-edit" #EDIT ME!
CONFIG_PATH="/home/matt/srt-auto-edit/settings.yaml" #EDIT ME!

# shellcheck disable=SC2001
files=$(echo "${MH_FILES%%,*}" | sed 's/[]"[]//g')

for file in "${files%%.*}"* ; do
  if [[ $file == *srt ]];
  then
    ${SCRIPT_PATH}/srtautoedit.py -c "${CONFIG_PATH}" -a -q -s "${file}"
  fi
done
