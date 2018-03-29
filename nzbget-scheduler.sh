#!/bin/bash

##############################################################################
### NZBGET SCHEDULER SCRIPT                                                ###

# SRT Auto Edit scheduler script.
#
# Applies a configuration of rules to modify SRT files.
#

##############################################################################
### OPTIONS                                                                ###

# Path to srt-auto-edit settings.yaml file
#
#SETTINGSYAML_PATH=

# Script arguments
#
#SCRIPT_ARGS=-s -q

# Directories to scan
#
# Space seperated directories to scan for SRT files to process.
#
#SCAN_DIRECTORIES=/data/media/TV /data/media/Movies

# Maximum age
#
# Maximum age of SRT files to process in minutes
#
#MAX_AGE=28800

### NZBGET SCHEDULER SCRIPT                                                ###
##############################################################################

echo "Running scheduled srt-auto-edit on files..."
find ${NZBPO_SCAN_DIRECTORIES} -name *.srt -cmin -${NZBPO_MAX_AGE} -exec python srtautoedit.py -c "$NZBPO_SETTINGSYAML_PATH" $NZBPO_SCRIPT_ARGS "{}" \;

# Exit good no matter what
exit 93
