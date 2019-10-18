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
# Include the file name
#SETTINGSYAML_PATH=

# Path to directory that contains the srtautoedit.py file
#
# No trailing slash
#SRTAUTOEDIT_PATH=

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

read -r -a script_args <<< "$NZBPO_SCRIPT_ARGS"
read -r -a scan_directories <<< "$NZBPO_SCAN_DIRECTORIES"

echo "Running scheduled srt-auto-edit on files..."
find "${scan_directories[@]}" -name \*.srt -cmin "-${NZBPO_MAX_AGE}" -exec "${NZBPO_SRTAUTOEDIT_PATH}/srtautoedit.py" -c "${NZBPO_SETTINGSYAML_PATH}" "${script_args[@]}" "{}" \;

# Exit good no matter what
exit 93
