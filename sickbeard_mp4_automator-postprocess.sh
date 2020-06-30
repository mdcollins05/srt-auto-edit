#!/bin/bash
set -euo pipefail

# Run srt-auto-edit against any subtitle files included for sickbeard_mp4_automator

SCRIPT_PATH="/home/matt/srt-auto-edit" #EDIT ME!
CONFIG_PATH="/home/matt/srt-auto-edit/settings.yaml" #EDIT ME!

files="${SMA_FILES:=${MH_FILES:=[]}}" # Support old and new env variable from Sickbeard MP4 Automator

echo "${files}" | jq -c '.[]' | while read -r file; do
  file=$(sed -e 's/"//g' <<<"${file}")
  if [[ $file == *srt ]]; then
    ${SCRIPT_PATH}/srtautoedit.py -c "${CONFIG_PATH}" -a -q -s "${file}"
  fi
done
