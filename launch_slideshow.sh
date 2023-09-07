#!/bin/bash

res=`ps ux | grep 'vue' | grep -v 'grep'`

if [[ -z $res ]]; then
    if ! screen -list | grep -q "live"; then
	screen -S 'live'
	sleep 5
    fi
    screen -S 'live' -X stuff "cd /home/ycheah/Documents/DST-showcase-repo
"
    screen -S 'live' -X stuff "./killrun.sh
"
    screen -S 'live' -X stuff "clear
"
    screen -S 'live' -X stuff "./run.sh
"
else
    echo > /dev/null
    # Nothing
fi
   
