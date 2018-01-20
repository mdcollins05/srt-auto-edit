#!/bin/bash

##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Clean up srt files with srt-auto-edit

##############################################################################
#### OPTIONS                                                               ###

# Path to srt-auto-edit settings.yaml file
#SETTINGSYAML_PATH=

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################

#Clean the mkv (will make a clean.<filename>

echo "Running srt-auto-edit on files..."
python srtautoedit.py -c "$NZBPO_SETTINGSYAML_PATH" "$NZBPP_DIRECTORY"

# Exit good no matter what
exit 93
