#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Run srt-auto-edit against any subtitle files included with video file for Sonarr

# shellcheck disable=SC2154
DESTINATION=${sonarr_series_path}
SCRIPT_PATH="/home/matt/srt-auto-edit" #EDIT ME!
CONFIG_PATH="/home/matt/srt-auto-edit/settings.yaml" #EDIT ME!

${SCRIPT_PATH}/srtautoedit.py -c "${CONFIG_PATH}" -a -s -q "${DESTINATION}"
