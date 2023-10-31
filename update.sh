#!/bin/bash
while true
do  
    # old repo reference
    # git pull ssh://git@bitbucket.org/yocheah/dst-showcase-repo.git

    # only pull from public repo.
    git pull https://github.com/lbl-usi/hallway-display.git
    sleep 150
done

