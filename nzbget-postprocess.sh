#!/bin/bash

##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# SRT Auto Edit post-process script.
#
# Applies a configuration of rules to modify SRT files.

##############################################################################
#### OPTIONS                                                               ###

# Path to srt-auto-edit settings.yaml file
#SETTINGSYAML_PATH=

# Script arguments
#SCRIPT_ARGS=-s -q

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################

echo "Running post-process srt-auto-edit on files..."
python srtautoedit.py -c "$NZBPO_SETTINGSYAML_PATH" $NZBPO_SCRIPT_ARGS "$NZBPP_DIRECTORY"

# Exit good no matter what
exit 93
