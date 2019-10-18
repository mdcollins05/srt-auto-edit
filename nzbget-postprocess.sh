#!/bin/bash

##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# SRT Auto Edit post-process script.
#
# Applies a configuration of rules to modify SRT files.

##############################################################################
#### OPTIONS                                                               ###

# Path to srt-auto-edit settings.yaml file
#
# Include the file name
#SETTINGSYAML_PATH=

# Path to directory that contains the srtautoedit.py file
#
# No trailing slash
#SRTAUTOEDIT_PATH=

# Script arguments
#SCRIPT_ARGS=-s -q

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################

read -r -a script_args <<< "$NZBPO_SCRIPT_ARGS"

echo "Running post-process srt-auto-edit on files..."
"${NZBPO_SRTAUTOEDIT_PATH}/srtautoedit.py" -c "${NZBPO_SETTINGSYAML_PATH}" "${script_args[@]}" "${NZBPP_DIRECTORY}"

# Exit good no matter what
exit 93
