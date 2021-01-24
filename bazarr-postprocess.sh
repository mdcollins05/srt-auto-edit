#!/bin/bash

#echo "Subtitle file is: '${1}'"

/home/matt/srt-auto-edit/srtautoedit.py -c /home/matt/srt-auto-edit/settings.yaml -a -s -v "${1}"
