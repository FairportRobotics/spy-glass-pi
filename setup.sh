#!/bin/bash

echo -n "Step: "
read step

if [$step == 1]; then
    sudo apt update && sudo apt full-upgrade
    sudo apt install imx500-all imx500-tools
    sudo apt install python3-opencv python3-munkres
    sudo reboot
elif [$step == 2]; then
    imx500-package -i packerOut.zip -o output
else
    echo "Invalid step"
fi
